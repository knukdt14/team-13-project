"""첨부 파일 파싱과 SQLite 영속화."""

from __future__ import annotations

import uuid

from src.backend.db.repository import Repository
from src.backend.errors import InvalidFileError, NotFoundError
from src.backend.schemas import AttachmentInfo, DeleteResponse
from src.ingest.documents import read_image, read_pdf
from src.shared.constants import SUPPORTED_IMAGE_SUFFIXES

PREVIEW_LIMIT = 400
EXCERPT_LIMIT = 1800


class DocumentService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def add(self, session_id: str, filename: str, data: bytes) -> AttachmentInfo:
        if not data:
            raise InvalidFileError(f"빈 파일이에요: {filename}")
        lower = filename.lower()
        if lower.endswith(".pdf"):
            text, pages, note = read_pdf(data)
            kind = "pdf"
        elif lower.endswith(SUPPORTED_IMAGE_SUFFIXES):
            text, note = read_image(data)
            pages, kind = 0, "image"
        else:
            raise InvalidFileError(f"PDF 또는 이미지 파일만 올릴 수 있어요: {filename}")
        session_id = self.repository.ensure_session(session_id)
        doc_id = uuid.uuid4().hex[:12]
        self.repository.add_attachment(doc_id, session_id, filename, kind, text, pages, note)
        return AttachmentInfo(
            doc_id=doc_id, session_id=session_id, filename=filename, kind=kind,
            pages=pages, chars=len(text), preview=text[:PREVIEW_LIMIT], note=note,
        )

    def list(self, session_id: str) -> list[AttachmentInfo]:
        return [self._info(row) for row in self.repository.attachments(session_id)]

    def delete(self, session_id: str, doc_id: str) -> DeleteResponse:
        if not self.repository.delete_attachment(session_id, doc_id):
            raise NotFoundError("첨부 문서를 찾을 수 없어요.")
        return DeleteResponse(doc_id=doc_id)

    def context(self, session_id: str, doc_ids: list[str] | None = None) -> str:
        rows = [row for row in self.repository.attachments(session_id, doc_ids) if row["text"]]
        if not rows:
            return ""
        budget = EXCERPT_LIMIT // len(rows)
        return "\n\n".join(
            f"[{'PDF' if row['kind'] == 'pdf' else '이미지'}] {row['filename']}\n"
            f"{row['text'][:budget]}{'…' if len(row['text']) > budget else ''}"
            for row in rows
        )

    @staticmethod
    def _info(row) -> AttachmentInfo:
        text = row["text"]
        return AttachmentInfo(
            doc_id=row["doc_id"], session_id=row["session_id"], filename=row["filename"],
            kind=row["kind"], pages=row["pages"], chars=len(text), preview=text[:PREVIEW_LIMIT],
            note=row["note"],
        )
