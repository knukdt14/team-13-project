"""정책 카드·상세·목록 응답 계약."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PolicyCard(BaseModel):
    plcy_no: str
    title: str
    organization: str
    categories: list[str] = Field(default_factory=list)
    age_label: str = "나이 무관"
    period_label: str = "기간 미정"
    days_left: int | None = None
    status: str | None = None
    jobs: list[str] = Field(default_factory=list)
    schools: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    summary: str = ""
    apply_url: str | None = None


class PolicyDetail(PolicyCard):
    keywords: list[str] = Field(default_factory=list)
    body: str = ""
    raw: dict = Field(default_factory=dict)


class PolicyListResponse(BaseModel):
    total: int = Field(ge=0, description="조건을 걸지 않은 전체 정책 수")
    matched: int = Field(ge=0, description="조건에 맞는 정책 수")
    page: int = Field(ge=1)
    size: int = Field(ge=1)
    items: list[PolicyCard] = Field(default_factory=list)
