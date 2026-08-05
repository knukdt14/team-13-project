"""FastAPI 애플리케이션 조립 지점.

라우터는 모두 ``/api`` 아래에 등록하고, SPA는 가장 마지막에 마운트한다.

컨테이너 분리 후 이 프로세스는 임베딩 모델도 FAISS 인덱스도 올리지 않는다.
무거운 일은 AI 서비스(``src.ai.main``)가 맡고, 여기서는 그쪽으로 연결할
HTTP 클라이언트만 준비한다. 덕분에 백엔드는 몇 초 만에 뜬다.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.backend.config import settings
from src.backend.errors import install_error_handlers
from src.backend.services.ai_client import AIClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """DB를 준비하고 AI 서비스 연결을 하나만 만들어 재사용한다."""
    from src.backend.db.database import initialize_database

    initialize_database()
    application.state.ai = AIClient(settings.ai_service_url)
    logger.info("AI 서비스 연결 준비: %s", settings.ai_service_url)

    # 기동을 막지는 않는다. AI가 아직 모델을 읽는 중이어도 정책 목록·지도·
    # 자격 진단은 즉시 서비스되어야 한다.
    state = application.state.ai.health()
    if state.get("retriever_ready"):
        logger.info("AI 서비스 준비 완료 · 정책 %s건", state.get("policies"))
    else:
        logger.warning(
            "AI 서비스가 아직 준비되지 않았습니다(챗봇만 영향): %s",
            state.get("retriever_error"),
        )
    try:
        yield
    finally:
        application.state.ai.close()


def create_app(*, mount_spa: bool = True) -> FastAPI:
    from src.backend.routers import chat, documents, meta, policies, regions, sessions

    application = FastAPI(
        title="청년정책도우미 API",
        description="맞춤 정책 검색 · RAG 상담 · 문서 · 지역 탐색",
        version="1.0.0",
        lifespan=lifespan,
    )
    install_error_handlers(application)

    for module in (meta, chat, policies, regions, documents, sessions):
        application.include_router(module.router, prefix="/api")

    dist = settings.frontend_dist
    if mount_spa and dist.exists():
        application.mount("/", StaticFiles(directory=dist, html=True), name="spa")
    return application


app = create_app()
