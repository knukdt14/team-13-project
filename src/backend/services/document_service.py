"""첨부 파일 파싱과 SQLite 영속화."""

from __future__ import annotations

import io
import re
import sys
import uuid

from src.backend.db.repository import Repository
from src.backend.errors import InvalidFileError, NotFoundError
from src.backend.schemas import AttachmentInfo, DeleteResponse
from src.shared.constants import SUPPORTED_IMAGE_SUFFIXES

PREVIEW_LIMIT = 400
EXCERPT_LIMIT = 1800
_ocr_reader = None


def read_pdf(data: bytes) -> tuple[str, int, str]:
    """ingest 패키지 초기화와 분리된 요청 시점 PDF 파서."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    text = re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()
    note = "" if text else "텍스트를 추출하지 못했어요. 스캔 이미지 PDF일 수 있어요."
    return text, len(reader.pages), note


def read_image(data: bytes) -> tuple[str, str]:
    """EasyOCR 모델을 최초 이미지 요청에서 한 번만 준비한다."""
    global _ocr_reader
    try:
        import easyocr
        import numpy as np
        from PIL import Image
    except ImportError as error:
        # 백엔드 이미지를 가볍게 유지하려고 OCR 의존성(torch 계열)은 넣지 않는다.
        # 이미지 인식(F4·P3)을 켜려면 requirements.api.txt 에 easyocr 를 추가한다.
        raise InvalidFileError(
            "이미지 인식(OCR) 기능이 이 서버에 설치되어 있지 않아요. PDF로 올려주세요."
        ) from error

    if _ocr_reader is None:
        for stream in (sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)
            if callable(reconfigure):
                try:
                    reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        # Windows 콘솔에서 진행률 문자 인코딩으로 죽지 않도록 반드시 끈다.
        _ocr_reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
    lines = _ocr_reader.readtext(
        np.array(Image.open(io.BytesIO(data)).convert("RGB")),
        detail=0,
        paragraph=True,
    )
    text = re.sub(r"[ \t]+", " ", "\n".join(str(line) for line in lines)).strip()
    note = "" if text else "글자를 찾지 못했어요. 더 선명한 사진으로 다시 올려보세요."
    return text, note


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
