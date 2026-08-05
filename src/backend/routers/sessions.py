"""대화 이력과 피드백 라우터."""

from fastapi import APIRouter, Depends

from src.backend.db.repository import Repository
from src.backend.deps import get_repository
from src.backend.schemas import FeedbackRequest, Message, OkResponse

router = APIRouter(tags=["sessions"])


@router.get("/sessions/{session_id}/messages", response_model=list[Message], summary="대화 이력")
def messages(
    session_id: str, repository: Repository = Depends(get_repository)
) -> list[Message]:
    return repository.messages(session_id)


@router.post("/feedback", response_model=OkResponse, summary="답변 평가")
def feedback(
    body: FeedbackRequest, repository: Repository = Depends(get_repository)
) -> OkResponse:
    repository.add_feedback(body.message_id, body.score)
    return OkResponse(message="평가를 남겼어요.")
