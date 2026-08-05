"""API 전반에서 공유하는 작은 응답 모델."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class OkResponse(BaseModel):
    ok: bool = True
    message: str = ""


class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"


class HealthResponse(BaseModel):
    ok: bool = True
    policies: int = 0
    rag_mode: str = "unavailable"
    retriever_ready: bool = False
    generator_ready: bool = False
    # 컨테이너 분리 후, AI가 별도 서비스이므로 어디에 붙었고 왜 실패했는지 노출한다.
    ai_service_url: str = ""
    ai_error: str | None = None


class Page(BaseModel, Generic[T]):
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)
    items: list[T] = Field(default_factory=list)
