"""첨부 파일 파싱과 SQLite 영속화.

PDF 는 가벼워서 여기서 직접 읽는다. 이미지 OCR 은 easyocr → torch 를 끌고
오므로 이 컨테이너에 두지 않고, torch 가 이미 있는 AI 서비스에 맡긴다.
"""

from __future__ import annotations

import io
import re
import uuid
from typing import TYPE_CHECKING

from src.backend.db.repository import Repository
from src.backend.errors import InvalidFileError, NotFoundError
from src.backend.schemas import AttachmentInfo, DeleteResponse
from src.shared.constants import SUPPORTED_IMAGE_SUFFIXES

if TYPE_CHECKING:
    from src.backend.services.ai_client import AIClient

PREVIEW_LIMIT = 400
EXCERPT_LIMIT = 1800


def read_pdf(data: bytes) -> tuple[str, int, str]:
    """ingest 패키지 초기화와 분리된 요청 시점 PDF 파서."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    text = re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()
    note = "" if text else "텍스트를 추출하지 못했어요. 스캔 이미지 PDF일 수 있어요."
    return text, len(reader.pages), note


class DocumentService:
    def __init__(self, repository: Repository, ai: "AIClient | None" = None):
        self.repository = repository
        # 이미지 첨부일 때만 필요하다. PDF·목록·삭제는 AI 없이 동작한다.
        self.ai = ai

    def read_image(self, data: bytes, filename: str) -> tuple[str, str]:
        """OCR 은 AI 서비스에 위임한다."""
        if self.ai is None:
            raise InvalidFileError(
                "이미지 인식을 맡은 AI 서비스에 연결되지 않았어요. PDF로 올려주세요."
            )
        return self.ai.ocr(data, filename)

    def add(self, session_id: str, filename: str, data: bytes) -> AttachmentInfo:
        if not data:
            raise InvalidFileError(f"빈 파일이에요: {filename}")
        lower = filename.lower()
        if lower.endswith(".pdf"):
            text, pages, note = read_pdf(data)
            kind = "pdf"
        elif lower.endswith(SUPPORTED_IMAGE_SUFFIXES):
            text, note = self.read_image(data, filename)
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
