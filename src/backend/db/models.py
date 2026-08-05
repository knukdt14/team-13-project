"""DB 행을 서비스 값으로 전달할 때 쓰는 가벼운 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SessionRow:
    id: str
    created_at: datetime


@dataclass(frozen=True)
class AttachmentRow:
    doc_id: str
    session_id: str
    filename: str
    kind: str
    text: str
    pages: int
    note: str
