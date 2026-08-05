"""AI 서비스 어댑터 및 대화 저장 오케스트레이션.

컨테이너 분리 후, 이 서비스가 AI 컨테이너에 HTTP로 물어보는 것은 두 가지뿐이다.

    1) 정책 검색   ai.search(...)          FAISS 인덱스와 임베딩 모델이 필요
    2) 답변 생성   ai.stream_generate(...) Solar API 호출이 필요

정책 원본 조회와 자격 판정은 모델이 필요 없는 순수 계산이므로 백엔드가 직접
한다(``policy_service.policy_records`` · ``PolicyFilter``). 덕분에 정책 목록·
지도·자격 진단은 AI 컨테이너가 죽어 있어도 정상 동작한다.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter
from typing import Any

from src.backend.db.repository import Repository
from src.backend.errors import RAGUnavailableError
from src.backend.schemas import (
    AskRequest,
    AskResponse,
    EligibilityResponse,
    SearchResult,
    Source,
    UserProfile,
)
from src.backend.services.ai_client import AIClient
from src.backend.services.document_service import DocumentService
from src.backend.services.policy_service import (
    is_nationwide,
    policy_records,
    policy_to_card,
    profile_filters,
)
from src.rag.eligibility import PolicyFilter


@lru_cache(maxsize=1)
def _policy_filter() -> PolicyFilter:
    """모델이 필요 없는 순수 판정기. 백엔드 프로세스에서 직접 쓴다."""
    return PolicyFilter()


@dataclass
class PreparedAnswer:
    request: AskRequest
    search: SearchResult
    policies: list[dict[str, Any]]
    conditions: dict[str, Any]
    history: list[dict[str, str]]
    session_id: str
    attachment_text: str

    @property
    def has_evidence(self) -> bool:
        return bool(self.policies or self.attachment_text)


class ChatService:
    def __init__(self, repository: Repository, ai: AIClient | None = None):
        self.repository = repository
        self.ai = ai
        self.documents = DocumentService(repository)

    def _require_ai(self) -> AIClient:
        if self.ai is None:
            raise RAGUnavailableError("AI 서비스가 연결되지 않았어요.")
        return self.ai

    @staticmethod
    def _source(result: dict[str, Any], raw_policy: dict[str, Any] | None) -> Source:
        metadata = result.get("metadata") or {}
        start, end = metadata.get("application_start"), metadata.get("application_end")
        period = (
            f"{start} – {end}" if start and end
            else metadata.get("application_type") or "기간 미정"
        )
        return Source(
            plcy_no=str(result.get("policy_id") or ""),
            title=str(result.get("policy_name") or "이름 없는 정책"),
            organization=str(metadata.get("organization") or "기관 미상"),
            category=str(metadata.get("large_category") or "기타"),
            apply_url=metadata.get("application_url") or metadata.get("reference_url"),
            apply_period=period,
            snippet=" ".join(str(result.get("matched_text") or "").split())[:400],
            score=float(result.get("score") or 0.0),
            policy=policy_to_card(raw_policy) if raw_policy else None,
        )

    def _search(self, request: AskRequest) -> tuple[SearchResult, list[dict[str, Any]], dict[str, Any]]:
        profile = request.profile or UserProfile()
        filters = profile_filters(profile)
        # 정책 원본은 백엔드도 갖고 있다. AI 응답에는 policy_id 만 오므로
        # 카드 변환·전국 판정은 이 로컬 사전으로 처리한다.
        records = policy_records()

        # AI 서비스에는 include_nationwide 옵션이 없다. 기존 API와 지도에서
        # 검증된 동작을 유지하기 위해 지역 조건이 있을 때 넉넉히 검색한 뒤,
        # 전국 정책을 백엔드에서 제거하고 요청한 top_k만 남긴다.
        search_top_k = request.top_k
        exclude_nationwide = bool(profile.region and not request.include_nationwide)
        if exclude_nationwide:
            search_top_k = max(request.top_k * 5, 25)

        raw = self._require_ai().search(
            request.question,
            top_k=search_top_k,
            filters=filters or None,
            include_closed=request.include_closed,
            mode=request.mode.value,
        )
        policies = list(raw.get("policies") or [])
        if exclude_nationwide:
            policies = [
                item for item in policies
                if not is_nationwide(records.get(str(item.get("policy_id")), {}))
            ]
        policies = policies[: request.top_k]

        sources = [
            self._source(item, records.get(str(item.get("policy_id"))))
            for item in policies
        ]
        result = SearchResult(
            sources=sources,
            matched_policies=[source.plcy_no for source in sources],
            matched=len(policies),
            total=len(records),
            relevant=bool(policies),
        )
        conditions = dict(raw.get("extracted_conditions") or filters)
        return result, policies, conditions

    def _prepare(self, request: AskRequest) -> PreparedAnswer:
        session_id = self.repository.ensure_session(request.session_id)
        history = [
            {"role": message.role, "content": message.content}
            for message in self.repository.messages(session_id)
            if message.role in {"user", "assistant"}
        ][-6:]
        attachment_text = self.documents.context(session_id, request.doc_ids)
        search, policies, conditions = self._search(request)
        self.repository.add_message(session_id, "user", request.question)
        return PreparedAnswer(
            request=request,
            search=search,
            policies=policies,
            conditions=conditions,
            history=history,
            session_id=session_id,
            attachment_text=attachment_text,
        )

    @staticmethod
    def _attachment_policy(text: str) -> dict[str, Any]:
        return {
            "policy_id": "attachment",
            "policy_name": "첨부 문서",
            "score": 1.0,
            "matched_text": text,
            "metadata": {
                "application_start": None,
                "application_end": None,
                "is_open": True,
                "organization": "사용자 첨부",
                "income_condition": None,
                "income_details": None,
                "application_url": None,
                "reference_url": None,
            },
        }

    def _ensure_generator(self, prepared: PreparedAnswer) -> None:
        if prepared.has_evidence:
            self._require_ai().require_generator()

    def _tokens(self, prepared: PreparedAnswer) -> Iterator[str]:
        if not prepared.has_evidence:
            yield "질문과 조건에 맞는 정책 근거를 찾지 못했어요. 조건을 조금 넓혀 다시 물어보세요."
            return
        policies = list(prepared.policies)
        if prepared.attachment_text:
            policies.insert(0, self._attachment_policy(prepared.attachment_text))
        yield from self._require_ai().stream_generate(
            prepared.request.question,
            prepared.conditions,
            policies,
            prepared.history,
        )

    def ask(self, request: AskRequest) -> AskResponse:
        started = perf_counter()
        prepared = self._prepare(request)
        self._ensure_generator(prepared)
        answer = "".join(self._tokens(prepared))
        response = AskResponse(
            answer=answer,
            sources=prepared.search.sources,
            matched_policies=prepared.search.matched_policies,
            session_id=prepared.session_id,
            elapsed_ms=int((perf_counter() - started) * 1000),
            matched=prepared.search.matched,
            total=prepared.search.total,
            relevant=prepared.has_evidence,
            generated=prepared.has_evidence,
            used_attachments=bool(prepared.attachment_text),
        )
        self.repository.add_message(
            prepared.session_id, "assistant", answer, prepared.search.sources
        )
        return response

    def stream(
        self, request: AskRequest
    ) -> tuple[Iterator[str], SearchResult, str, bool, bool]:
        prepared = self._prepare(request)
        # StreamingResponse가 시작된 뒤 실패하면 HTTP 상태를 503으로 바꿀 수 없다.
        # 생성기 준비 여부는 반드시 첫 SSE 바이트를 보내기 전에 검사한다.
        self._ensure_generator(prepared)

        def tokens() -> Iterator[str]:
            chunks: list[str] = []
            for token in self._tokens(prepared):
                chunks.append(token)
                yield token
            self.repository.add_message(
                prepared.session_id,
                "assistant",
                "".join(chunks),
                prepared.search.sources,
            )

        return (
            tokens(),
            prepared.search,
            prepared.session_id,
            bool(prepared.attachment_text),
            prepared.has_evidence,
        )

    def eligibility(self, profile: UserProfile) -> EligibilityResponse:
        """모델이 필요 없는 순수 판정. AI 컨테이너가 꺼져 있어도 동작한다."""
        conditions = profile_filters(profile)
        policy_filter = _policy_filter()
        eligible = [
            policy_id
            for policy_id, policy in policy_records().items()
            if policy_filter.matches(policy, conditions, include_closed=False)
            and not (profile.region and is_nationwide(policy))
        ]
        return EligibilityResponse(
            eligible_policy_ids=eligible,
            matched=len(eligible),
            reasons=[
                "팀 RAG의 자격 필터로 나이·취업상태·학력·소득 조건을 확인했어요.",
                "지역을 선택했다면 전국 정책은 기본적으로 제외했어요.",
            ],
        )
