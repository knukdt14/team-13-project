"""사용자 질문에서 정책 검색용 조건을 규칙 기반으로 추출한다.

LLM 없이도 재현 가능하게 동작하는 기본 구현이다. 추후 백엔드가 Solar 등으로
조건을 추출한다면 ``PolicyRetriever.search(..., filters=...)``에 같은 필드로
전달하면 된다.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


# 데이터의 zipCd는 2026년 행정구역 코드를 사용한다. 광주·전남은 통합 코드 12이다.
REGION_PREFIXES: dict[str, tuple[str, ...]] = {
    "서울": ("11",),
    "광주": ("12",),
    "전남": ("12",),
    "부산": ("26",),
    "대구": ("27",),
    "인천": ("28",),
    "대전": ("30",),
    "울산": ("31",),
    "세종": ("36",),
    "경기": ("41",),
    "충북": ("43",),
    "충남": ("44",),
    "경북": ("47",),
    "경남": ("48",),
    "제주": ("50",),
    "강원": ("51",),
    "전북": ("52",),
}

REGION_ALIASES: dict[str, tuple[str, ...]] = {
    "서울": ("서울", "서울시", "서울특별시"),
    "광주": ("광주", "광주시", "광주광역시"),
    "전남": ("전남", "전라남도"),
    "부산": ("부산", "부산시", "부산광역시"),
    "대구": ("대구", "대구시", "대구광역시"),
    "인천": ("인천", "인천시", "인천광역시"),
    "대전": ("대전", "대전시", "대전광역시"),
    "울산": ("울산", "울산시", "울산광역시"),
    "세종": ("세종", "세종시", "세종특별자치시"),
    "경기": ("경기", "경기도"),
    "충북": ("충북", "충청북도"),
    "충남": ("충남", "충청남도"),
    "경북": ("경북", "경상북도"),
    "경남": ("경남", "경상남도"),
    "제주": ("제주", "제주도", "제주특별자치도"),
    "강원": ("강원", "강원도", "강원특별자치도"),
    "전북": ("전북", "전라북도", "전북특별자치도"),
}

JOB_KEYWORDS: dict[str, tuple[str, ...]] = {
    "미취업자": ("미취업자", "미취업", "구직자", "취준생", "취업 준비", "무직", "백수"),
    "재직자": ("재직자", "재직 중", "재직", "직장인", "회사원"),
    "자영업자": ("자영업", "소상공인"),
    "프리랜서": ("프리랜서",),
    "일용근로자": ("일용근로", "일용직"),
    "단기근로자": ("단기근로", "단기 알바", "아르바이트", "알바생", "알바"),
    "(예비)창업자": ("예비창업", "창업 준비", "창업자"),
    "영농종사자": ("영농", "농업인", "농부"),
}

SCHOOL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "고졸 미만": ("중학생", "중학교 졸업", "고졸 미만"),
    "고교 재학": ("고등학생", "고교 재학", "고등학교 재학"),
    "고졸 예정": ("고졸 예정", "고등학교 졸업 예정"),
    "고교 졸업": ("고졸", "고등학교 졸업"),
    "대학 재학": ("대학생", "대학 재학", "대학교 재학"),
    "대졸 예정": ("대졸 예정", "대학교 졸업 예정"),
    "대학 졸업": ("대졸", "대학교 졸업", "대학 졸업"),
    "석·박사": ("대학원생", "석사", "박사"),
}

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "주거": ("주거", "월세", "전세", "보증금", "주택"),
    "일자리": ("일자리", "취업", "구직", "채용", "인턴", "창업"),
    "교육": ("교육", "훈련", "자격증", "수강료"),
    "금융･복지･문화": ("금융", "대출", "복지", "문화", "생활비"),
    "참여･기반": ("참여", "권리", "커뮤니티", "정책 참여"),
}


@dataclass
class SearchConditions:
    age: int | None = None
    region: str | None = None
    employment: str | None = None
    education: str | None = None
    income_bracket: int | None = None
    marriage: str | None = None
    category: str | None = None

    def to_dict(self, drop_none: bool = True) -> dict[str, Any]:
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None} if drop_none else result


class ConditionExtractor:
    """한국어 질문에서 검색에 쓸 명시적 조건을 추출한다."""

    AGE_PATTERNS = (
        re.compile(r"(?:만\s*)?(\d{1,2})\s*(?:세|살)"),
        re.compile(r"나이(?:는|가)?\s*(\d{1,2})"),
    )

    def extract(self, question: str) -> tuple[SearchConditions, str]:
        if not question or not question.strip():
            raise ValueError("질문을 입력해 주세요.")

        normalized = " ".join(question.strip().split())
        job_status = self._first_keyword(normalized, JOB_KEYWORDS)
        category_text = normalized
        if job_status:
            for phrase in JOB_KEYWORDS[job_status]:
                category_text = category_text.replace(phrase, " ")
        conditions = SearchConditions(
            age=self._extract_age(normalized),
            region=self._first_keyword(normalized, REGION_ALIASES),
            employment=job_status,
            education=self._first_keyword(normalized, SCHOOL_KEYWORDS),
            income_bracket=self._extract_income_bracket(normalized),
            marriage=self._extract_marriage(normalized),
            category=self._first_keyword(category_text, CATEGORY_KEYWORDS),
        )
        return conditions, self._make_search_text(normalized, conditions)

    @classmethod
    def _extract_age(cls, text: str) -> int | None:
        for pattern in cls.AGE_PATTERNS:
            match = pattern.search(text)
            if match:
                age = int(match.group(1))
                if 0 <= age <= 99:
                    return age
        return None

    @staticmethod
    def _extract_income_bracket(text: str) -> int | None:
        match = re.search(r"(?:기준\s*)?중위소득\s*(\d{1,3})\s*%", text)
        if match:
            value = int(match.group(1))
            return value if 0 <= value <= 999 else None
        return None

    @staticmethod
    def _first_keyword(text: str, mapping: dict[str, tuple[str, ...]]) -> str | None:
        # 긴 표현부터 검사해 "광주"보다 "광주광역시" 같은 명시적 표현을 우선한다.
        matches: list[tuple[int, int, str]] = []
        for canonical, aliases in mapping.items():
            for alias in aliases:
                position = text.find(alias)
                if position >= 0:
                    matches.append((position, -len(alias), canonical))
        return min(matches)[2] if matches else None

    @staticmethod
    def _extract_marriage(text: str) -> str | None:
        if any(word in text for word in ("미혼", "결혼 안", "결혼하지 않")):
            return "미혼"
        if any(word in text for word in ("기혼", "결혼했", "배우자")):
            return "기혼"
        return None

    @staticmethod
    def _make_search_text(text: str, conditions: SearchConditions) -> str:
        cleaned = text
        cleaned = re.sub(r"(?:만\s*)?\d{1,2}\s*(?:세|살)", " ", cleaned)
        cleaned = re.sub(r"나이(?:는|가)?\s*\d{1,2}", " ", cleaned)

        removable: list[str] = []
        if conditions.region:
            removable.extend(REGION_ALIASES[conditions.region])
        if conditions.employment:
            removable.extend(JOB_KEYWORDS[conditions.employment])
        if conditions.education:
            removable.extend(SCHOOL_KEYWORDS[conditions.education])
        if conditions.income_bracket is not None:
            cleaned = re.sub(
                r"(?:기준\s*)?중위소득\s*\d{1,3}\s*%", " ", cleaned
            )

        for phrase in sorted(removable, key=len, reverse=True):
            cleaned = cleaned.replace(phrase, " ")

        cleaned = re.sub(
            r"\b(?:저는|나는|제가|내가|저|나|거주|살고|사는|인데|입니다|이에요|예요)\b",
            " ",
            cleaned,
        )
        cleaned = " ".join(cleaned.split()).strip(" ,.?을를은는이가에에서")
        return cleaned or text
