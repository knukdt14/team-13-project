"""구조화 정책 파일 조회와 API 카드 변환.

정확 조건 판정은 팀 RAG의 ``PolicyFilter``를 사용한다. 목록·메타·지도는
FAISS 인덱스가 없어도 동작해야 하므로 ``PolicyRetriever``에는 의존하지 않는다.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from functools import lru_cache
from typing import Any, Mapping

from src.backend.errors import NotFoundError
from src.backend.schemas import (
    CodesResponse,
    GeoJsonResponse,
    MetaResponse,
    PolicyCard,
    PolicyDetail,
    PolicyListResponse,
    RegionCount,
    RegionSummaryResponse,
    SidoOption,
    UserProfile,
)
from src.rag.core.data_loader import load_policies
from src.rag.eligibility import PolicyFilter
from src.shared.constants import ANY_VALUE, NATIONWIDE_MIN_CODES, SIDO
from src.shared.paths import CODE_DEFINITIONS, PROVINCES_GEOJSON, STRUCTURED_POLICIES

RAG_REGION_BY_CODE = {
    "11": "서울", "12": "광주", "26": "부산", "27": "대구", "28": "인천",
    "30": "대전", "31": "울산", "36": "세종", "41": "경기", "43": "충북",
    "44": "충남", "47": "경북", "48": "경남", "50": "제주", "51": "강원",
    "52": "전북",
}


@lru_cache(maxsize=1)
def policy_records() -> dict[str, dict[str, Any]]:
    return load_policies(STRUCTURED_POLICIES)


def profile_filters(profile: UserProfile | None) -> dict[str, Any]:
    """RAG 필터와 이름이 같은 값만, 빈 값 없이 전달한다."""
    if profile is None:
        return {}
    filters = {
        key: value
        for key, value in profile.model_dump().items()
        if value is not None and value != ""
    }
    region = str(filters.get("region") or "")
    code = None
    if region:
        code = region[:2] if region[:2] in SIDO else next(
            (item for item, name in SIDO.items() if region == name or region in name),
            None,
        )
    # UserProfile은 코드·정식 명칭도 받지만 팀 PolicyFilter는 짧은 표준명만 받는다.
    if code:
        filters["region"] = RAG_REGION_BY_CODE[code]
    return filters


def is_nationwide(policy: Mapping[str, Any]) -> bool:
    codes = policy.get("zipCdList") or policy.get("zipCd") or []
    if not isinstance(codes, list):
        codes = [part.strip() for part in str(codes).split(",") if part.strip()]
    return len(codes) >= NATIONWIDE_MIN_CODES


def _categories(value: Any) -> list[str]:
    seen: list[str] = []
    for item in str(value or "").split(","):
        item = item.strip()
        if item and item not in seen:
            seen.append(item)
    return seen


def _period_label(policy: Mapping[str, Any]) -> str:
    if policy.get("aplyPrdSeCdNm") == "상시" or policy.get("aplyPrdSeCd") == "0057002":
        return "상시 모집"
    start, end = policy.get("aplyStartYmd"), policy.get("aplyEndYmd")
    if start and end:
        return f"{start} – {end}"
    return str(policy.get("aplyPrdSeCdNm") or "기간 미정")


def _days_left(policy: Mapping[str, Any]) -> int | None:
    try:
        return (date.fromisoformat(str(policy["aplyEndYmd"])[:10]) - date.today()).days
    except (KeyError, TypeError, ValueError):
        return None


def policy_to_card(policy: Mapping[str, Any]) -> PolicyCard:
    zip_codes = policy.get("zipCdList") or policy.get("zipCd") or []
    if not isinstance(zip_codes, list):
        zip_codes = [part.strip() for part in str(zip_codes).split(",") if part.strip()]
    regions = ["전국"] if is_nationwide(policy) else sorted(
        {SIDO[str(code)[:2]] for code in zip_codes if str(code)[:2] in SIDO}
    )
    age_label = "나이 무관"
    if policy.get("sprtTrgtAgeLmtYn") == "Y":
        minimum, maximum = policy.get("sprtTrgtMinAge"), policy.get("sprtTrgtMaxAge")
        if minimum and maximum:
            age_label = f"{minimum}–{maximum}세"
    summary = " ".join(
        str(policy.get("plcyExplnCn") or policy.get("plcySprtCn") or "").split()
    )
    return PolicyCard(
        plcy_no=str(policy.get("plcyNo") or ""),
        title=str(policy.get("plcyNm") or "이름 없는 정책"),
        organization=str(
            policy.get("operInstCdNm") or policy.get("rgtrInstCdNm") or "기관 미상"
        ),
        categories=_categories(policy.get("lclsfNm")),
        age_label=age_label,
        period_label=_period_label(policy),
        days_left=_days_left(policy),
        status=policy.get("aplyPrdSeCdNm"),
        jobs=list(policy.get("jobCdNmList") or []),
        schools=list(policy.get("schoolCdNmList") or []),
        regions=regions,
        summary=summary[:160] + ("…" if len(summary) > 160 else ""),
        apply_url=policy.get("aplyUrlAddr") or policy.get("refUrlAddr1"),
    )


def policy_to_generator_payload(policy: Mapping[str, Any]) -> dict[str, Any]:
    """구조화 정책 하나를 답변 생성기가 읽는 형태로 바꾼다.

    후속 질문("3번 정책 신청 방법")에서는 다시 검색하지 않고 지목된 정책만
    생성기에 넘긴다. 그때 ``PolicyRetriever.search`` 가 돌려주던 것과 같은
    모양을 백엔드가 직접 만들어야 하므로 이 함수가 필요하다.
    """
    body = "\n".join(
        str(policy.get(field) or "")
        for field in ("plcyExplnCn", "plcySprtCn", "plcyAplyMthdCn", "aplyBnfLmtCn")
        if policy.get(field)
    )
    remaining = _days_left(policy)
    return {
        "policy_id": str(policy.get("plcyNo") or ""),
        "policy_name": str(policy.get("plcyNm") or "이름 없는 정책"),
        "score": 1.0,
        "matched_text": body,
        "metadata": {
            "application_start": policy.get("aplyStartYmd"),
            "application_end": policy.get("aplyEndYmd"),
            "application_type": policy.get("aplyPrdSeCdNm"),
            "is_open": remaining is None or remaining >= 0,
            "organization": policy.get("operInstCdNm") or policy.get("rgtrInstCdNm"),
            "large_category": policy.get("lclsfNm"),
            "income_condition": policy.get("earnCndSeCdNm"),
            "income_details": policy.get("earnEtcCn"),
            "application_url": policy.get("aplyUrlAddr"),
            "reference_url": policy.get("refUrlAddr1") or policy.get("refUrlAddr2"),
        },
    }


class PolicyService:
    def __init__(self) -> None:
        self.filter = PolicyFilter()

    @property
    def total(self) -> int:
        return len(policy_records())

    def meta(self) -> MetaResponse:
        jobs: set[str] = set()
        schools: set[str] = set()
        for policy in policy_records().values():
            jobs.update(policy.get("jobCdNmList") or [])
            schools.update(policy.get("schoolCdNmList") or [])
        return MetaResponse(
            total=self.total,
            jobs=sorted(value for value in jobs if value and value != ANY_VALUE),
            schools=sorted(value for value in schools if value and value != ANY_VALUE),
            sido=[SidoOption(code=code, name=name) for code, name in SIDO.items()],
        )

    def codes(self) -> CodesResponse:
        return CodesResponse(codes=json.loads(CODE_DEFINITIONS.read_text(encoding="utf-8")))

    def _matching(
        self,
        profile: UserProfile,
        *,
        query: str | None,
        include_closed: bool,
        include_nationwide: bool,
    ) -> list[dict[str, Any]]:
        conditions = profile_filters(profile)
        found: list[dict[str, Any]] = []
        for policy in policy_records().values():
            if (
                profile.region
                and not include_nationwide
                and is_nationwide(policy)
            ):
                continue
            if not self.filter.matches(policy, conditions, include_closed):
                continue
            if query:
                haystack = " ".join(
                    str(policy.get(field) or "")
                    for field in (
                        "plcyNm", "plcyKywdNm", "plcyExplnCn", "plcySprtCn", "lclsfNm"
                    )
                ).lower()
                if query.strip().lower() not in haystack:
                    continue
            found.append(policy)
        return found

    def list(
        self, profile: UserProfile, *, query: str | None, include_closed: bool,
        include_nationwide: bool, page: int, size: int,
    ) -> PolicyListResponse:
        found = self._matching(
            profile, query=query, include_closed=include_closed,
            include_nationwide=include_nationwide,
        )
        start = (page - 1) * size
        return PolicyListResponse(
            total=self.total, matched=len(found), page=page, size=size,
            items=[policy_to_card(item) for item in found[start : start + size]],
        )

    def detail(self, plcy_no: str) -> PolicyDetail:
        policy = policy_records().get(plcy_no)
        if policy is None:
            raise NotFoundError(f"정책을 찾을 수 없어요: {plcy_no}")
        card = policy_to_card(policy)
        body = "\n".join(
            str(policy.get(field) or "")
            for field in ("plcyExplnCn", "plcySprtCn", "plcyAplyMthdCn")
            if policy.get(field)
        )
        return PolicyDetail(
            **card.model_dump(),
            keywords=[
                item.strip() for item in str(policy.get("plcyKywdNm") or "").split(",")
                if item.strip()
            ],
            body=body,
            raw=dict(policy),
        )

    def region_summary(
        self, profile: UserProfile, *, query: str | None, include_closed: bool
    ) -> RegionSummaryResponse:
        profile = profile.model_copy(update={"region": None})
        found = self._matching(
            profile, query=query, include_closed=include_closed,
            include_nationwide=True,
        )
        tally: Counter[str] = Counter()
        nationwide = 0
        for policy in found:
            if is_nationwide(policy):
                nationwide += 1
                continue
            codes = policy.get("zipCdList") or []
            for code in {str(value)[:2] for value in codes}:
                if code in SIDO:
                    tally[code] += 1
        regions = [
            RegionCount(code=code, name=name, count=tally.get(code, 0))
            for code, name in SIDO.items()
        ]
        regions.sort(key=lambda item: -item.count)
        return RegionSummaryResponse(
            matched=len(found), max=max((item.count for item in regions), default=0),
            nationwide=nationwide, regions=regions,
        )

    def provinces(self) -> GeoJsonResponse:
        if not PROVINCES_GEOJSON.exists():
            raise NotFoundError("provinces.geojson이 없어요. ingest geo 명령을 먼저 실행해주세요.")
        return GeoJsonResponse.model_validate_json(PROVINCES_GEOJSON.read_text(encoding="utf-8"))
