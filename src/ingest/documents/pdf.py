"""PDF 본문 추출."""

from __future__ import annotations

import io
import re


def _tidy(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def read_pdf(data: bytes) -> tuple[str, int, str]:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("PDF 처리를 위해 pypdf가 필요합니다.") from error
    reader = PdfReader(io.BytesIO(data))
    text = _tidy("\n\n".join(page.extract_text() or "" for page in reader.pages))
    note = "" if text else "텍스트를 추출하지 못했어요. 스캔 이미지 PDF일 수 있어요."
    return text, len(reader.pages), note
