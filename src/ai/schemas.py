"""백엔드 ↔ AI 서비스 사이의 계약.

``src/backend/schemas`` 가 프론트↔백엔드 계약이듯, 이 파일은 백엔드↔AI 계약이다.
이 파일은 AI 서비스가 소유하며, 백엔드 쪽 구현은
``src/backend/services/ai_client.py`` 다. 한쪽을 고치면 반드시 다른 쪽도 맞춘다.

RAG 내부 구조(policies 배열의 세부 필드)는 팀 RAG가 소유한다. 여기서는
``PolicyRetriever.search`` 의 반환값을 그대로 통과시키고 형태만 고정한다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """``PolicyRetriever.search`` 인자를 그대로 옮긴 요청."""

    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=200)
    filters: dict[str, Any] | None = None
    include_closed: bool = False
    mode: str = Field(default="hybrid", pattern="^(vector|bm25|hybrid)$")


class SearchResponse(BaseModel):
    """``PolicyRetriever.search`` 반환값."""

    question: str = ""
    search_text: str = ""
    extracted_conditions: dict[str, Any] = Field(default_factory=dict)
    top_k: int = 0
    result_count: int = 0
    search_mode: str = "hybrid"
    policies: list[dict[str, Any]] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    """``SolarGenerator.stream_answer`` 인자를 그대로 옮긴 요청."""

    question: str = Field(min_length=1, max_length=2000)
    conditions: dict[str, Any] = Field(default_factory=dict)
    policies: list[dict[str, Any]] = Field(default_factory=list)
    history: list[dict[str, str]] = Field(default_factory=list)


class InterpretRequest(BaseModel):
    """검색 전에 "이 입력이 무엇인지" 를 묻는 요청.

    정책은 제목만 보낸다. 본문까지 보내면 해석이 느려지고, 해석에는 제목이면
    충분하다.
    """

    question: str = Field(min_length=1, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list)
    recent_policies: list[dict[str, Any]] = Field(default_factory=list)
    profile: dict[str, Any] = Field(default_factory=dict)


class InterpretResponse(BaseModel):
    """해석 결과.

    ``ok=False`` 면 해석에 실패한 것이다. 백엔드는 이때 기존 동작(무조건 검색)
    으로 되돌아간다. 그래서 이 엔드포인트는 실패해도 200 으로 응답한다.
    """

    intent: str = "search"
    standalone_question: str = ""
    policy_ids: list[str] = Field(default_factory=list)
    conditions: dict[str, Any] = Field(default_factory=dict)
    ok: bool = False
    error: str = ""


class OcrResponse(BaseModel):
    """포스터·현수막 사진에서 뽑아낸 텍스트."""

    text: str = ""
    note: str = ""
    chars: int = 0


class AIHealthResponse(BaseModel):
    """백엔드가 기동 순서와 503 판정에 쓰는 준비 상태."""

    ok: bool = False
    retriever_ready: bool = False
    generator_ready: bool = False
    policies: int = 0
    chunks: int = 0
    device: str = ""
    retriever_error: str | None = None
    generator_error: str | None = None


# 스트리밍 한 줄의 형태. 정상 토큰은 {"t": "..."} , 실패는 {"error": "..."} 이다.
TOKEN_KEY = "t"
ERROR_KEY = "error"

__all__ = [
    "AIHealthResponse",
    "ERROR_KEY",
    "GenerateRequest",
    "InterpretRequest",
    "InterpretResponse",
    "OcrResponse",
    "SearchRequest",
    "SearchResponse",
    "TOKEN_KEY",
]
