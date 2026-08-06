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
    application_url: str | None = Field(
        default=None, description="기관의 신청 페이지 주소",
    )
    reference_url: str | None = Field(
        default=None, description="정책 공고·상세 페이지 주소",
    )
    can_apply_directly: bool = Field(
        default=False, description="신청 페이지 주소 제공 여부",
    )
    documents: list[str] = Field(
        default_factory=list,
        description="기관이 공고에 적어 둔 제출 서류를 항목별로 나눈 것. 문구는 원문 그대로다.",
    )
    view_count: int = Field(
        default=0,
        description="온통청년에서 수집한 시점의 누적 조회수. 실시간이 아니다.",
    )


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
