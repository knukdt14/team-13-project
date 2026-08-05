"""SQLite 쿼리를 한곳에 모은다."""

from __future__ import annotations

import json
import sqlite3
import uuid

from src.backend.schemas import Message, Source


class Repository:
    def __init__(self, database: sqlite3.Connection):
        self.database = database

    def ensure_session(self, session_id: str = "") -> str:
        session_id = session_id or uuid.uuid4().hex
        self.database.execute("INSERT OR IGNORE INTO sessions(id) VALUES (?)", (session_id,))
        return session_id

    def add_message(
        self, session_id: str, role: str, content: str, sources: list[Source] | None = None
    ) -> int:
        cursor = self.database.execute(
            "INSERT INTO messages(session_id, role, content, sources_json) VALUES (?, ?, ?, ?)",
            (session_id, role, content, json.dumps([item.model_dump() for item in sources or []], ensure_ascii=False)),
        )
        return int(cursor.lastrowid)

    def messages(self, session_id: str) -> list[Message]:
        rows = self.database.execute(
            "SELECT id, session_id, role, content, sources_json, created_at FROM messages WHERE session_id=? ORDER BY id",
            (session_id,),
        ).fetchall()
        return [
            Message(
                id=row["id"], session_id=row["session_id"], role=row["role"],
                content=row["content"], sources=[Source.model_validate(item) for item in json.loads(row["sources_json"])],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def add_attachment(
        self, doc_id: str, session_id: str, filename: str, kind: str,
        text: str, pages: int, note: str,
    ) -> None:
        self.database.execute(
            "INSERT INTO attachments(doc_id, session_id, filename, kind, text, pages, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (doc_id, session_id, filename, kind, text, pages, note),
        )

    def attachments(self, session_id: str, doc_ids: list[str] | None = None) -> list[sqlite3.Row]:
        if doc_ids:
            placeholders = ",".join("?" for _ in doc_ids)
            return self.database.execute(
                f"SELECT * FROM attachments WHERE session_id=? AND doc_id IN ({placeholders}) ORDER BY created_at",  # noqa: S608 - placeholders only
                (session_id, *doc_ids),
            ).fetchall()
        return self.database.execute(
            "SELECT * FROM attachments WHERE session_id=? ORDER BY created_at", (session_id,)
        ).fetchall()

    def delete_attachment(self, session_id: str, doc_id: str) -> bool:
        cursor = self.database.execute(
            "DELETE FROM attachments WHERE session_id=? AND doc_id=?", (session_id, doc_id)
        )
        return cursor.rowcount > 0

    def add_feedback(self, message_id: int, score: int) -> None:
        self.database.execute(
            "INSERT INTO feedback(message_id, score) VALUES (?, ?)", (message_id, score)
        )
