"""지역 집계와 GeoJSON 라우터."""

from fastapi import APIRouter, Query

from src.backend.schemas import GeoJsonResponse, RegionSummaryResponse, UserProfile
from src.backend.services.policy_service import PolicyService

router = APIRouter(tags=["regions"])
service = PolicyService()


@router.get("/regions/summary", response_model=RegionSummaryResponse, summary="시도별 정책 수")
def summary(
    age: int | None = Query(default=None, ge=0, le=120),
    employment: str | None = None,
    education: str | None = None,
    q: str | None = None,
    include_closed: bool = False,
) -> RegionSummaryResponse:
    return service.region_summary(
        UserProfile(age=age, employment=employment, education=education),
        query=q, include_closed=include_closed,
    )


@router.get("/geo/provinces", response_model=GeoJsonResponse, summary="시도 경계 GeoJSON")
def provinces() -> GeoJsonResponse:
    return service.provinces()
