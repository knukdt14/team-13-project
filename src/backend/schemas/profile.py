"""사용자 조건과 검색 방식 계약."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from src.shared.constants import YOUTH_MAX_AGE, YOUTH_MIN_AGE


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


class UserProfile(BaseModel):
    # 범위 근거는 src/shared/constants.py 에 적어 두었다. PolicyFilter 도
    # 같은 값을 쓴다. 여기만 넓히면 통과는 되는데 결과가 0건인 나이가 생긴다.
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
