"""정책 목록·상세 라우터."""

from fastapi import APIRouter, Query

from src.backend.schemas import PolicyDetail, PolicyListResponse, UserProfile
from src.backend.services.policy_service import PolicyService

router = APIRouter(prefix="/policies", tags=["policies"])
service = PolicyService()


@router.get("", response_model=PolicyListResponse, summary="조건으로 정책 찾기")
def policies(
    age: int | None = Query(default=None, ge=0, le=120),
    employment: str | None = None,
    education: str | None = None,
    region: str | None = None,
    q: str | None = None,
    include_closed: bool = False,
    include_nationwide: bool = False,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> PolicyListResponse:
    return service.list(
        UserProfile(age=age, employment=employment, education=education, region=region),
        query=q, include_closed=include_closed, include_nationwide=include_nationwide,
        page=page, size=size,
    )


@router.get("/{plcy_no}", response_model=PolicyDetail, summary="정책 상세")
def policy(plcy_no: str) -> PolicyDetail:
    return service.detail(plcy_no)
