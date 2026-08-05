"""FastAPI Depends 주입 함수."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request

from src.backend.db.database import connect
from src.backend.db.repository import Repository
from src.backend.errors import RAGUnavailableError
from src.backend.services.ai_client import AIClient


def get_repository() -> Iterator[Repository]:
    database = connect()
    try:
        yield Repository(database)
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


def get_ai_client(request: Request) -> AIClient:
    """AI 서비스 클라이언트. 연결 자체가 없으면 즉시 503으로 돌린다.

    실제 준비 상태(모델 적재 완료 여부)는 호출 직전에 ``require_*`` 로 확인한다.
    여기서 매번 health 를 부르면 정책 목록·지도까지 느려지기 때문이다.
    """
    client = getattr(request.app.state, "ai", None)
    if client is None:
        raise RAGUnavailableError("AI 서비스 연결이 초기화되지 않았어요.")
    return client
