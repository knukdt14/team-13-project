"""FastAPI Depends 주입 함수."""

from __future__ import annotations

from collections.abc import Iterator

from src.backend.db.database import connect
from src.backend.db.repository import Repository


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
