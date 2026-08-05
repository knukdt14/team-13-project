"""FastAPI 애플리케이션 조립 지점.

라우터는 모두 ``/api`` 아래에 등록하고, SPA는 가장 마지막에 마운트한다.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.backend.config import settings
from src.backend.errors import install_error_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """DB와 무거운 RAG 객체를 프로세스당 한 번만 준비한다."""
    from src.backend.db.database import initialize_database

    initialize_database()
    application.state.retriever = None
    application.state.generator = None
    application.state.retriever_error = None
    application.state.generator_error = None
    try:
        from src.rag.retriever import PolicyRetriever

        application.state.retriever = PolicyRetriever()
    except Exception as error:
        application.state.retriever_error = str(error)
        logger.warning("PolicyRetriever를 준비하지 못했습니다: %s", error)
    try:
        from src.rag.generator import SolarGenerator

        application.state.generator = SolarGenerator()
    except Exception as error:
        # API 키가 없어도 목록·메타·지도와 앱 기동은 정상이어야 한다.
        application.state.generator_error = str(error)
        logger.warning("SolarGenerator를 준비하지 못했습니다: %s", error)
    yield


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
