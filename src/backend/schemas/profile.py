"""사용자 조건과 검색 방식 계약."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    VECTOR = "vector"
    BM25 = "bm25"
    HYBRID = "hybrid"


class EmploymentStatus(str, Enum):
    EMPLOYED = "재직자"
    SELF_EMPLOYED = "자영업자"
    UNEMPLOYED = "미취업자"
    FREELANCER = "프리랜서"
    DAILY_WORKER = "일용근로자"
    FOUNDER = "(예비)창업자"
    SHORT_TERM = "단기근로자"
    FARMER = "영농종사자"
    OTHER = "기타"


# 실제 정책 데이터에서 뽑은 범위다. 청년기본법은 19~34세지만 지자체 조례가
# 더 넓게 잡는 경우가 많아 데이터가 훨씬 넓다.
#
#   나이 제한이 있는 정책 1,432건
#   하한  19세(814) · 18세(458) · 15세(60) · 17세(12)
#   상한  39세(890) · 45세(158) · 34세(136) · 49세(75)
#
# 상한을 45로 막으면 49세까지 받는 정책 75건이 잘린다.
YOUTH_MIN_AGE = 15
YOUTH_MAX_AGE = 49


class UserProfile(BaseModel):
    age: int | None = Field(
        default=None,
        ge=YOUTH_MIN_AGE,
        le=YOUTH_MAX_AGE,
        description=f"청년 나이 ({YOUTH_MIN_AGE}~{YOUTH_MAX_AGE}세)",
    )
    region: str | None = Field(default=None, description="시도 코드 또는 이름")
    employment: str | None = Field(default=None, description="jobCd 한글명")
    education: str | None = Field(default=None, description="schoolCd 한글명")
    income_bracket: int | None = Field(default=None, ge=0, description="중위소득 비율(%)")

    def is_empty(self) -> bool:
        return not any(
            value is not None and value != ""
            for value in (self.age, self.region, self.employment, self.education, self.income_bracket)
        )


class SidoOption(BaseModel):
    code: str
    name: str


class MetaResponse(BaseModel):
    total: int = Field(ge=0)
    jobs: list[str] = Field(default_factory=list)
    schools: list[str] = Field(default_factory=list)
    sido: list[SidoOption] = Field(default_factory=list)


class CodesResponse(BaseModel):
    codes: dict[str, dict[str, str]] = Field(default_factory=dict)
