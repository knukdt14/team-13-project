"""FastAPI 애플리케이션 조립 지점.

라우터는 모두 ``/api`` 아래에 등록하고, SPA는 가장 마지막에 마운트한다.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.backend.config import settings
from src.backend.errors import install_error_handlers


@asynccontextmanager
async def lifespan(_: FastAPI):
    """프로세스당 한 번 DB를 준비한다. RAG 실모델도 이 경계에서 준비한다."""
    from src.backend.db.database import initialize_database
    from src.rag import USE_STUB

    initialize_database()
    if USE_STUB:
        from src.rag.stub import load_policies

        load_policies()
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
