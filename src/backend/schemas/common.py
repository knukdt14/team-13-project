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


class Page(BaseModel, Generic[T]):
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)
    items: list[T] = Field(default_factory=list)
