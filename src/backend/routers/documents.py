"""첨부 문서 CRUD 라우터."""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from src.backend.db.repository import Repository
from src.backend.deps import get_ai_client, get_repository
from src.backend.schemas import AttachmentInfo, DeleteResponse, UploadResponse
from src.backend.services.ai_client import AIClient
from src.backend.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=UploadResponse, summary="PDF·이미지 첨부")
async def upload_documents(
    session_id: str = Form(...),
    files: list[UploadFile] = File(...),
    repository: Repository = Depends(get_repository),
    ai: AIClient = Depends(get_ai_client),
) -> UploadResponse:
    # 이미지 OCR 만 AI 서비스로 넘긴다. PDF 는 AI 가 꺼져 있어도 처리된다.
    service = DocumentService(repository, ai)
    items = [service.add(session_id, file.filename or "upload", await file.read()) for file in files]
    return UploadResponse(items=items)


@router.get("", response_model=list[AttachmentInfo], summary="첨부 목록")
def list_documents(
    session_id: str = Query(...), repository: Repository = Depends(get_repository)
) -> list[AttachmentInfo]:
    return DocumentService(repository).list(session_id)


@router.delete("/{doc_id}", response_model=DeleteResponse, summary="첨부 삭제")
def delete_document(
    doc_id: str,
    session_id: str = Query(...),
    repository: Repository = Depends(get_repository),
) -> DeleteResponse:
    return DocumentService(repository).delete(session_id, doc_id)
