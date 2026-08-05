"""질문·스트리밍·자격 진단 라우터."""

from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from src.backend.db.repository import Repository
from src.backend.deps import get_generator, get_repository, get_retriever
from src.backend.schemas import AskRequest, AskResponse, EligibilityResponse, SearchMode, UserProfile
from src.backend.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/ask", response_model=AskResponse, summary="정책 챗봇")
def ask(
    body: AskRequest,
    repository: Repository = Depends(get_repository),
    retriever: Any = Depends(get_retriever),
    generator: Any | None = Depends(get_generator),
) -> AskResponse:
    return ChatService(repository, retriever, generator).ask(body)


@router.get(
    "/ask/stream", response_model=str, response_class=StreamingResponse,
    summary="정책 챗봇 SSE 스트리밍",
)
def ask_stream(
    question: str = Query(min_length=1),
    session_id: str = "",
    age: int | None = Query(default=None, ge=0, le=120),
    region: str | None = None,
    employment: str | None = None,
    education: str | None = None,
    income_bracket: int | None = Query(default=None, ge=0),
    top_k: int = Query(default=5, ge=1, le=20),
    mode: SearchMode = SearchMode.HYBRID,
    doc_ids: list[str] = Query(default=[]),
    include_closed: bool = False,
    include_nationwide: bool = False,
    repository: Repository = Depends(get_repository),
    retriever: Any = Depends(get_retriever),
    generator: Any | None = Depends(get_generator),
) -> StreamingResponse:
    request = AskRequest(
        question=question, session_id=session_id,
        profile=UserProfile(
            age=age, region=region, employment=employment, education=education,
            income_bracket=income_bracket,
        ),
        top_k=top_k, mode=mode, doc_ids=doc_ids,
        include_closed=include_closed, include_nationwide=include_nationwide,
    )

    started = time.perf_counter()
    tokens, result, actual_session_id, used_attachments, generated = ChatService(
        repository, retriever, generator
    ).stream(request)

    def events():
        answer_parts: list[str] = []
        for token in tokens:
            answer_parts.append(token)
            yield f"event: token\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        payload = AskResponse(
            answer="".join(answer_parts), sources=result.sources,
            matched_policies=result.matched_policies, session_id=actual_session_id,
            elapsed_ms=int((time.perf_counter() - started) * 1000), matched=result.matched,
            total=result.total, relevant=result.relevant or used_attachments,
            generated=generated, used_attachments=used_attachments,
        )
        data = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False)
        yield f"event: done\ndata: {data}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/eligibility", response_model=EligibilityResponse, summary="정책 자격 진단")
def eligibility(
    profile: UserProfile,
    repository: Repository = Depends(get_repository),
    retriever: Any = Depends(get_retriever),
) -> EligibilityResponse:
    return ChatService(repository, retriever, None).eligibility(profile)
