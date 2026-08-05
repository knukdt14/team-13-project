"""메타데이터·코드·상태 라우터."""

from fastapi import APIRouter

from src.backend.config import settings
from src.backend.schemas import CodesResponse, HealthResponse, MetaResponse
from src.backend.services.policy_service import PolicyService
from src.rag import stub

router = APIRouter(tags=["meta"])
service = PolicyService()


@router.get("/meta", response_model=MetaResponse, summary="필터 선택지")
def meta() -> MetaResponse:
    return service.meta()


@router.get("/codes", response_model=CodesResponse, summary="정책 코드 정의")
def codes() -> CodesResponse:
    return service.codes()


@router.get("/health", response_model=HealthResponse, summary="상태 확인")
def health() -> HealthResponse:
    return HealthResponse(
        policies=len(stub.load_policies()), rag_mode="stub" if settings.rag_stub else "real"
    )
