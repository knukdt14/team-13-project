"""검색된 정책만 근거로 Solar 답변을 생성하고 스트리밍한다."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator, Sequence
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from .core.config import RAG_DIR
from .prompts import ATTACHMENT_MODE_HINT, SYSTEM_PROMPT

ATTACHMENT_POLICY_ID = "attachment"


class SolarGenerator:
    """Upstage Solar API를 호출하는 RAG 답변 생성기."""

    def __init__(self) -> None:
        load_dotenv(RAG_DIR / ".env")
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise RuntimeError("UPSTAGE_API_KEY가 없습니다. src/rag/.env 파일을 확인하세요.")

        self.model = os.getenv("UPSTAGE_MODEL", "solar-pro3")
        self.client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")

    def stream_answer(
        self,
        question: str,
        conditions: dict[str, Any],
        policies: list[dict[str, Any]],
        history: Sequence[dict[str, str]] = (),
    ) -> Iterator[str]:
        """최근 대화와 검색 정책을 전달하고 답변 조각을 순서대로 반환한다."""
        attachments = [item for item in policies if item.get("policy_id") == ATTACHMENT_POLICY_ID]
        search_hits = [item for item in policies if item.get("policy_id") != ATTACHMENT_POLICY_ID]

        context_sections = []
        if attachments:
            context_sections.append(f"[첨부 문서]\n{self._format_attachments(attachments)}")
        if search_hits:
            context_sections.append(f"[검색된 정책]\n{self._format_context(search_hits)}")
        context_text = "\n\n".join(context_sections) if context_sections else "근거 자료 없음"

        user_prompt = (
            f"사용자의 실제 질문:\n{question}\n\n"
            "검색에 사용된 조건:\n"
            f"{json.dumps(conditions, ensure_ascii=False)}\n\n"
            f"{context_text}"
        )
        system_prompt = SYSTEM_PROMPT + ATTACHMENT_MODE_HINT if attachments else SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": system_prompt},
            *history[-6:],
            {"role": "user", "content": user_prompt},
        ]
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=0.2,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    @staticmethod
    def _format_attachments(attachments: list[dict[str, Any]]) -> str:
        blocks = [str(item.get("matched_text") or "")[:4000] for item in attachments]
        return "\n\n---\n\n".join(block for block in blocks if block)

    @staticmethod
    def _format_context(policies: list[dict[str, Any]]) -> str:
        blocks: list[str] = []
        for number, policy in enumerate(policies, start=1):
            metadata = policy["metadata"]
            text = str(policy.get("matched_text") or "")[:4000]
            blocks.append(
                "\n".join(
                    [
                        f"[정책 {number}]",
                        f"정책 ID: {policy['policy_id']}",
                        f"정책명: {policy['policy_name']}",
                        f"유사도: {policy['score']}",
                        f"신청 기간: {metadata.get('application_start')} ~ "
                        f"{metadata.get('application_end')}",
                        f"접수 상태: {'접수 중' if metadata.get('is_open') else '마감/접수 전'}",
                        f"운영 기관: {metadata.get('organization')}",
                        f"소득 조건: {metadata.get('income_condition')} / "
                        f"{metadata.get('income_details')}",
                        f"신청 URL: {metadata.get('application_url')}",
                        f"참고 URL: {metadata.get('reference_url')}",
                        f"정책 내용:\n{text}",
                    ]
                )
            )
        return "\n\n".join(blocks)[:18000]


__all__ = ["SolarGenerator"]
