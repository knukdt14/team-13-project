"""SQLite 쿼리를 한곳에 모은다."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from src.backend.schemas import Message, Source


class Repository:
    def __init__(self, database: sqlite3.Connection):
        self.database = database

    def ensure_session(self, session_id: str = "") -> str:
        session_id = session_id or uuid.uuid4().hex
        self.database.execute("INSERT OR IGNORE INTO sessions(id) VALUES (?)", (session_id,))
        return session_id

    # ------------------------------------------------------- 세션에 쌓이는 조건

    def session_profile(self, session_id: str) -> dict[str, Any]:
        """대화 중 알게 된 사용자 조건. 요청마다 새로 받지 않고 누적한다."""
        row = self.database.execute(
            "SELECT profile_json FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        if row is None:
            return {}
        try:
            stored = json.loads(row["profile_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}
        return stored if isinstance(stored, dict) else {}

    def save_session_profile(self, session_id: str, profile: dict[str, Any]) -> None:
        self.database.execute(
            "UPDATE sessions SET profile_json=? WHERE id=?",
            (json.dumps(profile, ensure_ascii=False), session_id),
        )

    # ------------------------------------------------- 직전에 안내한 정책 목록

    def recent_sources(self, session_id: str) -> list[Source]:
        """가장 최근 답변에서 안내한 정책들.

        "3번 정책", "그 정책" 같은 표현을 실제 정책 ID 로 잇는 재료가 된다.
        정책을 안내하지 않은 답변(일반 대화)은 건너뛰고 거슬러 올라간다.
        """
        rows = self.database.execute(
            "SELECT sources_json FROM messages "
            "WHERE session_id=? AND role='assistant' ORDER BY id DESC LIMIT 5",
            (session_id,),
        ).fetchall()
        for row in rows:
            try:
                items = json.loads(row["sources_json"] or "[]")
            except (json.JSONDecodeError, TypeError):
                continue
            if items:
                return [Source.model_validate(item) for item in items]
        return []

    def shown_policy_ids(self, session_id: str) -> list[str]:
        """이번 대화에서 이미 안내한 모든 정책 번호.

        "다른 거 없어?" 라고 물었을 때 검색 결과에서 빼기 위해 쓴다.
        recent_sources 는 직전 한 번만 보지만, 여기서는 처음부터 전부 모은다.
        그래야 "다른 거"를 여러 번 물어도 계속 새로운 정책이 나온다.
        """
        rows = self.database.execute(
            "SELECT sources_json FROM messages "
            "WHERE session_id=? AND role='assistant' ORDER BY id",
            (session_id,),
        ).fetchall()
        seen: list[str] = []
        known: set[str] = set()
        for row in rows:
            try:
                items = json.loads(row["sources_json"] or "[]")
            except (json.JSONDecodeError, TypeError):
                continue
            for item in items:
                policy_id = str(item.get("plcy_no") or "")
                if policy_id and policy_id not in known:
                    known.add(policy_id)
                    seen.append(policy_id)
        return seen

    def add_message(
        self, session_id: str, role: str, content: str, sources: list[Source] | None = None
    ) -> int:
        cursor = self.database.execute(
            "INSERT INTO messages(session_id, role, content, sources_json) VALUES (?, ?, ?, ?)",
            (session_id, role, content, json.dumps([item.model_dump() for item in sources or []], ensure_ascii=False)),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("메시지 ID를 만들지 못했어요.")
        return cursor.lastrowid

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
