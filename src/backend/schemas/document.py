"""첨부 문서 API 계약."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AttachmentInfo(BaseModel):
    doc_id: str
    session_id: str
    filename: str
    kind: str = Field(pattern="^(pdf|image)$")
    pages: int = 0
    chars: int = 0
    preview: str = ""
    note: str = ""


class UploadResponse(BaseModel):
    items: list[AttachmentInfo] = Field(default_factory=list)


class DeleteResponse(BaseModel):
    deleted: bool = True
    doc_id: str
