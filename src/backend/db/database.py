"""SQLite 연결과 스키마 초기화."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from src.backend.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    profile_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sources_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS attachments (
    doc_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    pages INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    score INTEGER NOT NULL CHECK(score BETWEEN -1 AND 1),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_messages_session ON messages(session_id, id);
CREATE INDEX IF NOT EXISTS ix_attachments_session ON attachments(session_id);
"""


def connect() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    database = connect()
    try:
        yield database
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


# 이미 만들어진 app.db 에 칸을 덧붙이기 위한 목록.
# (테이블, 컬럼, ALTER 문) 이며 컬럼이 없을 때만 실행한다.
# 팀원이 각자 app.db 를 지우지 않아도 되도록 하기 위한 장치다.
MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "sessions",
        "profile_json",
        "ALTER TABLE sessions ADD COLUMN profile_json TEXT NOT NULL DEFAULT '{}'",
    ),
)


def _apply_migrations(database: sqlite3.Connection) -> None:
    for table, column, statement in MIGRATIONS:
        columns = {
            row["name"] for row in database.execute(f"PRAGMA table_info({table})")  # noqa: S608
        }
        if column not in columns:
            database.execute(statement)


def initialize_database() -> None:
    with connection() as database:
        database.executescript(SCHEMA)
        _apply_migrations(database)
