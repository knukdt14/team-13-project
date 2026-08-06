"""정책 목록·상세 라우터."""

from typing import Literal

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
    # 카테고리는 q 와 다르다. q 는 제목·키워드까지 훑지만 category 는 대분류만
    # 본다. 예전에는 탭이 q 로 "교육"을 보내서, 키워드가 '교육지원'인 일자리
    # 정책까지 교육 목록에 섞여 나왔다.
    category: str | None = None,
    include_closed: bool = False,
    include_nationwide: bool = False,
    direct_apply_only: bool = False,
    sort: Literal["default", "deadline"] = "default",
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> PolicyListResponse:
    return service.list(
        UserProfile(age=age, employment=employment, education=education, region=region),
        query=q, category=category,
        include_closed=include_closed, include_nationwide=include_nationwide,
        direct_apply_only=direct_apply_only, sort=sort, page=page, size=size,
    )


@router.get("/{plcy_no}", response_model=PolicyDetail, summary="정책 상세")
def policy(plcy_no: str) -> PolicyDetail:
    return service.detail(plcy_no)
