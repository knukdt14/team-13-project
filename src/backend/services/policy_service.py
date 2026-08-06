"""구조화 정책 파일 조회와 API 카드 변환.

정확 조건 판정은 팀 RAG의 ``PolicyFilter``를 사용한다. 목록·메타·지도는
FAISS 인덱스가 없어도 동작해야 하므로 ``PolicyRetriever``에는 의존하지 않는다.
"""

from __future__ import annotations

import json
import re
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
from src.shared.constants import (
    ANY_VALUE,
    NATIONWIDE_MIN_CODES,
    SIDO,
    YOUTH_MAX_AGE,
    YOUTH_MIN_AGE,
)
from src.shared.paths import (
    CODE_DEFINITIONS,
    DATA_DIR,
    PROVINCES_GEOJSON,
    STRUCTURED_POLICIES,
)

RAG_REGION_BY_CODE = {
    "11": "서울", "12": "광주", "26": "부산", "27": "대구", "28": "인천",
    "30": "대전", "31": "울산", "36": "세종", "41": "경기", "43": "충북",
    "44": "충남", "47": "경북", "48": "경남", "50": "제주", "51": "강원",
    "52": "전북",
}


@lru_cache(maxsize=1)
def policy_records() -> dict[str, dict[str, Any]]:
    return load_policies(STRUCTURED_POLICIES)


@lru_cache(maxsize=1)
def policy_summaries() -> dict[str, str]:
    """미리 만들어 둔 짧은 설명. `python -m src.ingest.build_summaries` 로 만든다.

    관공서 설명문은 마침표 없이 길게 이어져서 앞부분만 잘라 쓰면 말이 끊긴다.
    파일이 없으면 빈 사전을 돌려주고 원문을 잘라 쓴다. 없어도 동작해야 한다.
    """
    path = DATA_DIR / "policy_summaries.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


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


# 서술형 필드에 정보 대신 들어오는 값들. "제출서류: 없음"을 그대로 띄우면
# 서류가 필요 없다는 뜻으로 읽혀 오해를 부른다. 정리 단계가 아니라 여기서
# 거른다. EMPTY_PLACEHOLDERS 를 건드리면 RAG 문서까지 바뀌어 인덱스를 다시
# 만들어야 하고, LLM 에게는 "없음"도 유의미한 정보이기 때문이다.
_NO_INFO = {"없음", "미정", "0", "추후 공지", "추후공지", "별도 없음", "별도없음"}

# "1. 주민등록표 초본 ... 2. 건강보험 자격득실 확인서 ..." 처럼 번호가 매겨진
# 원문을 항목별로 자른다. 앞이 줄 시작이나 공백이어야 해서 "2026." 같은
# 연도는 걸리지 않는다.
_NUMBERED = re.compile(r"(?:^|\s)(\d{1,2})\.\s*")


def _documents(value: Any) -> list[str]:
    """제출 서류를 항목 목록으로 바꾼다.

    원문 형식이 세 가지다(874건 기준).
      번호형 203건 · 콤마형 281건 · 구분 없음 390건

    정리 단계에서 줄바꿈이 공백으로 눌리기 때문에 한 문단으로 뭉쳐 있다.
    그대로 두면 화면에서 읽을 수가 없어 여기서 나눈다. 문구는 손대지 않고
    끊기만 한다.
    """
    text = str(value or "").strip()
    if not text or text in _NO_INFO:
        return []

    parts = _NUMBERED.split(text)
    if len(parts) >= 5:  # [앞, 번호, 본문, 번호, 본문, ...] → 항목 2개 이상
        items = [part.strip(" ,·") for part in parts[2::2]]
        items = [item for item in items if item]
        if len(items) >= 2:
            return items

    # "구글폼 신청서, 공연 영상 이메일 제출" 처럼 짧게 나열된 경우만 콤마로 자른다.
    # 콜론이 있으면 "초본: 신청월 발급본, 발생일 포함"처럼 항목 안에 콤마가
    # 들어 있다는 뜻이라 자르지 않는다.
    if ":" not in text and len(text) <= 120 and "," in text:
        items = [part.strip() for part in text.split(",") if part.strip()]
        if len(items) >= 2 and all(len(item) <= 40 for item in items):
            return items

    return [text]


# "교통정책과", "경제산업과" 처럼 어느 지자체인지 없이 부서명만 오는 정책이
# 215건 있다. 이 경우 상위기관 필드(rgtrUpInstCdNm 등)도 비어 있어서, 카드에
# 부서명만 뜨면 어디서 하는 정책인지 알 수 없다. 지역명을 앞에 붙여 준다.
_DEPARTMENT_ONLY = re.compile(r"[가-힣]{2,8}(?:과|팀|계|담당관)$")


def _organization(policy: Mapping[str, Any], regions: list[str]) -> str:
    name = str(
        policy.get("operInstCdNm") or policy.get("rgtrInstCdNm") or ""
    ).strip()
    if not name:
        return "기관 미상"
    if _DEPARTMENT_ONLY.fullmatch(name) and regions and regions != ["전국"]:
        return f"{regions[0]} {name}"
    return name


def _summarize(value: Any, limit: int = 150) -> str:
    """카드에 넣을 한 문장을 만든다.

    전에는 150자에서 그냥 끊어서 단어 중간이 잘렸다. 문장 끝이 있으면 거기서,
    없으면 마지막 공백에서 끊는다. 화면에서는 CSS 가 두 줄로 한 번 더 줄이므로
    여기서는 문장이 어색하게 끊기지 않게만 한다.
    """
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text

    head = text[:limit]
    sentence_end = max(head.rfind("."), head.rfind("다 "), head.rfind("요 "))
    if sentence_end > limit * 0.5:
        return head[: sentence_end + 1].strip()

    space = head.rfind(" ")
    return (head[:space] if space > limit * 0.5 else head).rstrip() + "…"


def _period_label(policy: Mapping[str, Any]) -> str:
    if policy.get("aplyPrdSeCdNm") == "상시" or policy.get("aplyPrdSeCd") == "0057002":
        return "상시 모집"
    start, end = policy.get("aplyStartYmd"), policy.get("aplyEndYmd")
    if start and end:
        return f"{start} – {end}"
    return str(policy.get("aplyPrdSeCdNm") or "기간 미정")


def _view_count(policy: Mapping[str, Any]) -> int:
    try:
        return int(str(policy.get("inqCnt") or "0").strip())
    except ValueError:
        return 0


def _positive_age(value: Any) -> int | None:
    try:
        age = int(value)
    except (TypeError, ValueError):
        return None
    return age if age > 0 else None


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
    # 온통청년의 이 필드는 이름과 반대로 N이 제한 있음, Y가 제한 없음이다.
    # PolicyFilter와 같은 규칙으로 빈 경계만 서비스 청년 범위로 채운다.
    if policy.get("sprtTrgtAgeLmtYn") == "N":
        minimum = _positive_age(policy.get("sprtTrgtMinAge"))
        maximum = _positive_age(policy.get("sprtTrgtMaxAge"))
        if minimum is not None or maximum is not None:
            age_label = f"{minimum or YOUTH_MIN_AGE}–{maximum or YOUTH_MAX_AGE}세"
    # 미리 만들어 둔 요약이 있으면 그것을 쓰고, 없으면 원문을 잘라 쓴다.
    summary = policy_summaries().get(str(policy.get("plcyNo") or "")) or _summarize(
        policy.get("plcyExplnCn") or policy.get("plcySprtCn")
    )
    application_url = policy.get("aplyUrlAddr") or None
    reference_url = policy.get("refUrlAddr1") or policy.get("refUrlAddr2") or None
    return PolicyCard(
        plcy_no=str(policy.get("plcyNo") or ""),
        title=str(policy.get("plcyNm") or "이름 없는 정책"),
        organization=_organization(policy, regions),
        categories=_categories(policy.get("lclsfNm")),
        age_label=age_label,
        period_label=_period_label(policy),
        days_left=_days_left(policy),
        status=policy.get("aplyPrdSeCdNm"),
        jobs=list(policy.get("jobCdNmList") or []),
        schools=list(policy.get("schoolCdNmList") or []),
        regions=regions,
        summary=summary,
        # apply_url은 기존 프론트 호환용이다. 새 화면에서는 아래 두 주소를
        # 구분해 '바로 신청'과 '공고 보기' 문구를 정확히 표시한다.
        apply_url=application_url or reference_url,
        application_url=application_url,
        reference_url=reference_url,
        can_apply_directly=bool(application_url),
        documents=_documents(policy.get("sbmsnDcmntCn")),
        view_count=_view_count(policy),
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
        direct_apply_only: bool = False,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        conditions = profile_filters(profile)
        # PolicyFilter 가 대분류(lclsfNm)로만 판정한다. UserProfile 에 넣지 않는
        # 이유는 카테고리가 사용자 속성이 아니라 목록을 좁히는 조건이기 때문이다.
        if category:
            conditions["category"] = category
        found: list[dict[str, Any]] = []
        for policy in policy_records().values():
            if direct_apply_only and not policy.get("aplyUrlAddr"):
                continue
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
        direct_apply_only: bool = False, sort: str = "default",
        category: str | None = None,
    ) -> PolicyListResponse:
        found = self._matching(
            profile, query=query, include_closed=include_closed,
            include_nationwide=include_nationwide,
            direct_apply_only=direct_apply_only, category=category,
        )
        if sort == "popular":
            # inqCnt 는 온통청년에서 수집한 시점의 누적 조회수다. 우리 서비스의
            # 조회수가 아니고 실시간도 아니다. 화면 문구를 "실시간"이라고 쓰지
            # 않는 이유다.
            found.sort(key=_view_count, reverse=True)
        elif sort == "deadline":
            found.sort(key=lambda policy: (
                _days_left(policy) is None,
                _days_left(policy) if _days_left(policy) is not None else 10**9,
            ))
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
