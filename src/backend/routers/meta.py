"""메타데이터·코드·상태 라우터."""

from fastapi import APIRouter, Request

from src.backend.schemas import CodesResponse, HealthResponse, MetaResponse
from src.backend.services.policy_service import PolicyService

router = APIRouter(tags=["meta"])
service = PolicyService()


@router.get("/meta", response_model=MetaResponse, summary="필터 선택지")
def meta() -> MetaResponse:
    return service.meta()


@router.get("/codes", response_model=CodesResponse, summary="정책 코드 정의")
def codes() -> CodesResponse:
    return service.codes()


@router.get("/health", response_model=HealthResponse, summary="상태 확인")
def health(request: Request) -> HealthResponse:
    retriever_ready = getattr(request.app.state, "retriever", None) is not None
    generator_ready = getattr(request.app.state, "generator", None) is not None
    mode = "ready" if retriever_ready and generator_ready else (
        "search-only" if retriever_ready else "unavailable"
    )
    return HealthResponse(
        policies=service.total, rag_mode=mode,
        retriever_ready=retriever_ready, generator_ready=generator_ready,
    )
