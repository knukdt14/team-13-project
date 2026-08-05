"""첨부 문서 CRUD 라우터."""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from src.backend.db.repository import Repository
from src.backend.deps import get_repository
from src.backend.schemas import AttachmentInfo, DeleteResponse, UploadResponse
from src.backend.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=UploadResponse, summary="PDF·이미지 첨부")
async def upload_documents(
    session_id: str = Form(...),
    files: list[UploadFile] = File(...),
    repository: Repository = Depends(get_repository),
) -> UploadResponse:
    service = DocumentService(repository)
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
