"""FastAPI Depends 주입 함수."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import Request

from src.backend.db.database import connect
from src.backend.db.repository import Repository
from src.backend.errors import RAGUnavailableError


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


def get_retriever(request: Request) -> Any:
    retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        detail = getattr(request.app.state, "retriever_error", None)
        raise RAGUnavailableError(
            f"정책 검색기가 준비되지 않았어요. {detail or 'FAISS 인덱스를 확인해주세요.'}"
        )
    return retriever


def get_generator(request: Request) -> Any | None:
    """키가 없어도 앱과 검색 API가 뜨도록 생성기는 선택적으로 주입한다."""
    return getattr(request.app.state, "generator", None)
