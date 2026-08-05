"""RAG 호출과 대화 저장 오케스트레이션."""

from __future__ import annotations

from collections.abc import Iterator

from src import rag
from src.backend.db.repository import Repository
from src.backend.schemas import (
    AnswerResult,
    AskRequest,
    AskResponse,
    EligibilityResponse,
    SearchResult,
    UserProfile,
)
from src.backend.services.document_service import DocumentService
from src.rag import stub


class ChatService:
    def __init__(self, repository: Repository):
        self.repository = repository
        self.documents = DocumentService(repository)

    def ask(self, request: AskRequest) -> AskResponse:
        session_id = self.repository.ensure_session(request.session_id)
        self.repository.add_message(session_id, "user", request.question)
        result = rag.answer(
            request.question,
            request.profile or UserProfile(),
            session_id=session_id,
            attachments=self.documents.context(session_id, request.doc_ids),
            top_k=request.top_k,
            mode=request.mode,
            doc_ids=request.doc_ids,
            include_closed=request.include_closed,
            include_nationwide=request.include_nationwide,
        )
        response = AskResponse.model_validate(result.model_dump() if isinstance(result, AnswerResult) else result)
        self.repository.add_message(session_id, "assistant", response.answer, response.sources)
        return response

    def stream(self, request: AskRequest) -> tuple[Iterator[str], SearchResult, str, bool]:
        session_id = self.repository.ensure_session(request.session_id)
        self.repository.add_message(session_id, "user", request.question)
        profile = request.profile or UserProfile()
        attachments = self.documents.context(session_id, request.doc_ids)
        search_result = rag.search(
            request.question, profile, top_k=request.top_k, mode=request.mode,
            doc_ids=request.doc_ids, include_closed=request.include_closed,
            include_nationwide=request.include_nationwide,
        )

        def tokens() -> Iterator[str]:
            chunks: list[str] = []
            for token in rag.stream_answer(
                request.question, profile, session_id=session_id, attachments=attachments,
                top_k=request.top_k, mode=request.mode, doc_ids=request.doc_ids,
                include_closed=request.include_closed,
                include_nationwide=request.include_nationwide,
            ):
                chunks.append(token)
                yield token
            self.repository.add_message(
                session_id, "assistant", "".join(chunks), search_result.sources
            )

        return tokens(), search_result, session_id, bool(attachments)

    def eligibility(self, profile: UserProfile) -> EligibilityResponse:
        found = stub.filter_policies(profile)
        return EligibilityResponse(
            eligible_policy_ids=[str(item.get("plcyNo")) for item in found],
            matched=len(found),
            reasons=["나이 제한 여부를 먼저 확인했어요.", "취업상태·학력의 제한없음 정책도 포함했어요."],
        )
