"""질문·검색·대화 이력 계약."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.backend.schemas.policy import PolicyCard
from src.backend.schemas.profile import SearchMode, UserProfile


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str = ""
    profile: UserProfile | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    mode: SearchMode = SearchMode.HYBRID
    doc_ids: list[str] = Field(default_factory=list)
    include_closed: bool = False
    include_nationwide: bool = False


class Source(BaseModel):
    plcy_no: str
    title: str
    organization: str
    category: str = "기타"
    apply_url: str | None = None
    apply_period: str | None = None
    snippet: str = ""
    score: float = 0.0
    policy: PolicyCard | None = None


class SearchResult(BaseModel):
    sources: list[Source] = Field(default_factory=list)
    matched_policies: list[str] = Field(default_factory=list)
    matched: int = 0
    total: int = 0
    relevant: bool = False


class AnswerResult(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
    matched_policies: list[str] = Field(default_factory=list)
    session_id: str = ""
    elapsed_ms: int = 0
    matched: int = 0
    total: int = 0
    relevant: bool = False
    generated: bool = False
    used_attachments: bool = False


class AskResponse(AnswerResult):
    pass


class EligibilityResponse(BaseModel):
    eligible_policy_ids: list[str] = Field(default_factory=list)
    matched: int = 0
    reasons: list[str] = Field(default_factory=list)


class Message(BaseModel):
    id: int
    session_id: str
    role: Literal["user", "assistant", "system", "error"]
    content: str
    sources: list[Source] = Field(default_factory=list)
    created_at: datetime


class FeedbackRequest(BaseModel):
    message_id: int
    score: int = Field(ge=-1, le=1)
