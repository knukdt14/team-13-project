"""정책 파일 조회와 지역 집계."""

from __future__ import annotations

import json
from collections import Counter

from src.backend.errors import NotFoundError
from src.backend.schemas import (
    CodesResponse,
    GeoJsonResponse,
    MetaResponse,
    PolicyDetail,
    PolicyListResponse,
    RegionCount,
    RegionSummaryResponse,
    UserProfile,
)
from src.rag import stub
from src.shared.constants import SIDO
from src.shared.paths import CODE_DEFINITIONS, PROVINCES_GEOJSON


class PolicyService:
    def meta(self) -> MetaResponse:
        return MetaResponse.model_validate(stub.policy_options())

    def codes(self) -> CodesResponse:
        return CodesResponse(codes=json.loads(CODE_DEFINITIONS.read_text(encoding="utf-8")))

    def list(
        self, profile: UserProfile, *, query: str | None, include_closed: bool,
        include_nationwide: bool, page: int, size: int,
    ) -> PolicyListResponse:
        found = stub.filter_policies(
            profile, query=query, include_closed=include_closed,
            include_nationwide=include_nationwide,
        )
        start = (page - 1) * size
        return PolicyListResponse(
            total=len(stub.load_policies()), matched=len(found), page=page, size=size,
            items=[stub.to_policy_card(item) for item in found[start : start + size]],
        )

    def detail(self, plcy_no: str) -> PolicyDetail:
        for policy in stub.load_policies():
            if str(policy.get("plcyNo")) == plcy_no:
                card = stub.to_policy_card(policy)
                return PolicyDetail(
                    **card.model_dump(),
                    keywords=[item.strip() for item in str(policy.get("plcyKywdNm") or "").split(",") if item.strip()],
                    body=policy.get("_body") or "",
                    raw={key: value for key, value in policy.items() if not key.startswith("_")},
                )
        raise NotFoundError(f"정책을 찾을 수 없어요: {plcy_no}")

    def region_summary(
        self, profile: UserProfile, *, query: str | None, include_closed: bool
    ) -> RegionSummaryResponse:
        # 지도는 지역을 고르는 화면이므로 기존 지역 조건은 빼고 센다.
        profile = profile.model_copy(update={"region": None})
        found = stub.filter_policies(profile, query=query, include_closed=include_closed)
        tally: Counter[str] = Counter()
        nationwide = 0
        for policy in found:
            if stub.is_nationwide(policy):
                nationwide += 1
                continue
            for code in {str(value)[:2] for value in (policy.get("zipCdList") or [])}:
                if code in SIDO:
                    tally[code] += 1
        regions = [RegionCount(code=code, name=name, count=tally.get(code, 0)) for code, name in SIDO.items()]
        regions.sort(key=lambda item: -item.count)
        return RegionSummaryResponse(
            matched=len(found), max=max((item.count for item in regions), default=0),
            nationwide=nationwide, regions=regions,
        )

    def provinces(self) -> GeoJsonResponse:
        if not PROVINCES_GEOJSON.exists():
            raise NotFoundError("provinces.geojson이 없어요. ingest geo 명령을 먼저 실행해주세요.")
        return GeoJsonResponse.model_validate_json(PROVINCES_GEOJSON.read_text(encoding="utf-8"))
