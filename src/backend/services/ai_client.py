"""AI 서비스(별도 컨테이너)에 HTTP로 검색·생성을 요청하는 클라이언트.

컨테이너를 나누기 전에는 백엔드가 ``PolicyRetriever`` 객체를 직접 들고 있었다.
이 클래스는 그 자리에 그대로 들어가도록 같은 이름의 메서드를 제공한다.
호출부에서 보면 모양이 같고, 속만 HTTP 로 바뀐다.

    retriever.search(...)        ->  ai.search(...)
    generator.stream_answer(...) ->  ai.stream_generate(...)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

import httpx

from src.backend.errors import RAGUnavailableError

logger = logging.getLogger(__name__)

# 임베딩·LLM 호출은 느릴 수 있다. connect 는 짧게 잡아 죽은 서비스를 빨리
# 판별하고, read 는 넉넉히 준다(스트리밍에서는 조각 사이 간격에 적용된다).
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=180.0, write=30.0, pool=5.0)
HEALTH_TIMEOUT = httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=2.0)


class AIClient:
    """AI 서비스 HTTP 클라이언트. 앱 수명 동안 하나만 만들어 재사용한다."""

    def __init__(self, base_url: str, timeout: httpx.Timeout | None = None):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url, timeout=timeout or DEFAULT_TIMEOUT
        )

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------ 상태

    def health(self) -> dict[str, Any]:
        """준비 상태를 묻는다. 실패해도 예외 대신 사유가 담긴 dict를 준다."""
        try:
            response = self._client.get("/health", timeout=HEALTH_TIMEOUT)
            response.raise_for_status()
            return dict(response.json())
        except Exception as error:  # noqa: BLE001
            return {
                "ok": False,
                "retriever_ready": False,
                "generator_ready": False,
                "retriever_error": f"AI 서비스에 연결하지 못했어요({self.base_url}): {error}",
                "generator_error": None,
            }

    def require_retriever(self) -> None:
        state = self.health()
        if not state.get("retriever_ready"):
            raise RAGUnavailableError(
                f"정책 검색기가 준비되지 않았어요. {state.get('retriever_error') or ''}".strip()
            )

    def require_generator(self) -> None:
        """첫 바이트를 흘리기 전에 호출한다. 스트림 시작 후에는 503을 줄 수 없다."""
        state = self.health()
        if not state.get("generator_ready"):
            detail = state.get("generator_error") or state.get("retriever_error") or ""
            raise RAGUnavailableError(
                f"답변 생성기가 준비되지 않았어요. {detail}".strip()
            )

    # ------------------------------------------------------------------ 검색

    def search(
        self,
        question: str,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
        include_closed: bool = False,
        mode: str = "hybrid",
    ) -> dict[str, Any]:
        payload = {
            "question": question,
            "top_k": top_k,
            "filters": dict(filters) if filters else None,
            "include_closed": include_closed,
            "mode": mode,
        }
        try:
            response = self._client.post("/search", json=payload)
        except httpx.HTTPError as error:
            raise RAGUnavailableError(
                f"AI 서비스에 연결하지 못했어요({self.base_url}): {error}"
            ) from error
        if response.status_code >= 400:
            raise RAGUnavailableError(self._detail(response, "정책 검색에 실패했어요."))
        return dict(response.json())

    # ------------------------------------------------------------------ 생성

    def stream_generate(
        self,
        question: str,
        conditions: Mapping[str, Any],
        policies: Sequence[Mapping[str, Any]],
        history: Sequence[Mapping[str, str]] = (),
    ) -> Iterator[str]:
        """NDJSON 한 줄이 토큰 하나. 마지막 줄이 error 면 예외로 되살린다."""
        payload = {
            "question": question,
            "conditions": dict(conditions),
            "policies": [dict(item) for item in policies],
            "history": [dict(item) for item in history],
        }
        try:
            with self._client.stream("POST", "/generate", json=payload) as response:
                if response.status_code >= 400:
                    response.read()
                    raise RAGUnavailableError(
                        self._detail(response, "답변 생성에 실패했어요.")
                    )
                for line in response.iter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("AI 스트림에서 해석할 수 없는 줄: %r", line[:200])
                        continue
                    if "error" in data:
                        raise RAGUnavailableError(
                            f"답변 생성 중 오류가 났어요: {data['error']}"
                        )
                    token = data.get("t")
                    if token:
                        yield token
        except httpx.HTTPError as error:
            raise RAGUnavailableError(
                f"AI 서비스와의 연결이 끊겼어요({self.base_url}): {error}"
            ) from error

    # ------------------------------------------------------------------ OCR

    def ocr(self, data: bytes, filename: str = "image") -> tuple[str, str]:
        """이미지 바이트를 AI 서비스로 보내 텍스트를 받는다.

        easyocr 은 torch 를 끌고 오므로 백엔드에 두지 않는다. torch 가 이미
        있는 AI 컨테이너에서 처리하고 결과 문자열만 받아 온다.

        첫 호출은 easyocr 모델(약 100MB) 다운로드 때문에 느릴 수 있어
        읽기 제한 시간을 따로 넉넉히 준다.
        """
        try:
            response = self._client.post(
                "/ocr",
                params={"filename": filename},
                content=data,
                headers={"Content-Type": "application/octet-stream"},
                timeout=httpx.Timeout(connect=5.0, read=300.0, write=60.0, pool=5.0),
            )
        except httpx.HTTPError as error:
            raise RAGUnavailableError(
                f"이미지 인식을 맡은 AI 서비스에 연결하지 못했어요({self.base_url}): {error}"
            ) from error
        if response.status_code >= 400:
            raise RAGUnavailableError(
                self._detail(response, "이미지에서 글자를 읽지 못했어요.")
            )
        body = response.json()
        return str(body.get("text") or ""), str(body.get("note") or "")

    # ------------------------------------------------------------------ 내부

    @staticmethod
    def _detail(response: httpx.Response, fallback: str) -> str:
        try:
            body = response.json()
        except Exception:  # noqa: BLE001
            return f"{fallback} (HTTP {response.status_code})"
        if isinstance(body, dict) and body.get("detail"):
            return str(body["detail"])
        return f"{fallback} (HTTP {response.status_code})"


__all__ = ["AIClient"]
