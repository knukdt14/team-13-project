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
    """백엔드 자신과 AI 서비스의 상태를 한 번에 보여준다.

    AI가 죽어 있어도 이 엔드포인트는 200으로 응답해야 한다. compose 의
    의존성 판정과 시연 중 원인 파악에 쓰이기 때문이다.
    """
    client = getattr(request.app.state, "ai", None)
    state = client.health() if client is not None else {}
    retriever_ready = bool(state.get("retriever_ready"))
    generator_ready = bool(state.get("generator_ready"))
    mode = "ready" if retriever_ready and generator_ready else (
        "search-only" if retriever_ready else "unavailable"
    )
    return HealthResponse(
        policies=service.total, rag_mode=mode,
        retriever_ready=retriever_ready, generator_ready=generator_ready,
        ai_service_url=getattr(client, "base_url", ""),
        ai_error=state.get("retriever_error") or state.get("generator_error"),
    )
