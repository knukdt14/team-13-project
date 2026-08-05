"""정식 RAG가 준비될 때까지 쓰는 검증 완료 스텁.

``demo/policies.py``의 조건 필터와 ``demo/rag.py``의 낱말 겹침 검색을 옮겼다.
벡터 DB는 쓰지 않지만 백엔드·프론트엔드 계약은 정식 구현과 동일하다.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import date
from functools import lru_cache
from typing import Iterator

from src.backend.schemas import (
    AnswerResult,
    PolicyCard,
    SearchMode,
    SearchResult,
    Source,
    UserProfile,
)
from src.shared.constants import ANY_VALUE, NATIONWIDE_MIN_CODES, SIDO, sido_code
from src.shared.paths import RAG_DOCUMENTS, STRUCTURED_POLICIES

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
CONTEXT_SIZE = 4
MAX_NEW_TOKENS = 220

_bundle = None
_STOPWORDS = {
    "나에게", "저에게", "제가", "내가", "해당", "정책", "지원", "뭐가", "무엇",
    "있나요", "있어", "알려줘", "알려주세요", "어떤", "받을", "있는", "관련", "대해",
}


@lru_cache(maxsize=1)
def load_policies() -> list[dict]:
    policies = json.loads(STRUCTURED_POLICIES.read_text(encoding="utf-8"))
    docs = json.loads(RAG_DOCUMENTS.read_text(encoding="utf-8"))
    bodies = {str(item["plcyNo"]): item.get("text", "") for item in docs}
    return [{**item, "_body": bodies.get(str(item.get("plcyNo")), "")} for item in policies]


def age_ok(policy: dict, age: int | None) -> bool:
    """나이 제한 표시가 Y일 때만 범위를 검사한다."""
    if age is None or policy.get("sprtTrgtAgeLmtYn") != "Y":
        return True
    try:
        return int(policy["sprtTrgtMinAge"]) <= age <= int(policy["sprtTrgtMaxAge"])
    except (KeyError, TypeError, ValueError):
        return True


def code_ok(policy: dict, field: str, value: str | None) -> bool:
    """사용자 값과 일치하거나 정책 값에 '제한없음'이 있으면 통과한다."""
    if not value:
        return True
    names = policy.get(field) or []
    return not names or value in names or ANY_VALUE in names


def is_nationwide(policy: dict) -> bool:
    return len(policy.get("zipCdList") or []) >= NATIONWIDE_MIN_CODES


def region_ok(policy: dict, region: str | None, include_nationwide: bool = False) -> bool:
    code = sido_code(region)
    if not region:
        return True
    if code is None:
        return False
    if is_nationwide(policy) and not include_nationwide:
        return False
    return any(str(item).startswith(code) for item in (policy.get("zipCdList") or []))


def open_ok(policy: dict, include_closed: bool) -> bool:
    if include_closed:
        return True
    if policy.get("aplyPrdSeCd") == "0057003" or policy.get("aplyPrdSeCdNm") == "마감":
        return False
    if policy.get("aplyPrdSeCd") == "0057002" or policy.get("aplyPrdSeCdNm") == "상시":
        return True
    end = policy.get("aplyEndYmd")
    if end:
        try:
            return date.fromisoformat(end) >= date.today()
        except ValueError:
            pass
    return True


def query_ok(policy: dict, query: str | None) -> bool:
    if not query:
        return True
    haystack = " ".join(
        filter(None, (policy.get("plcyNm"), policy.get("plcyKywdNm"), policy.get("_body")))
    ).lower()
    return query.strip().lower() in haystack


def filter_policies(
    profile: UserProfile | None = None,
    *,
    query: str | None = None,
    include_closed: bool = False,
    include_nationwide: bool = False,
) -> list[dict]:
    profile = profile or UserProfile()
    return [
        policy
        for policy in load_policies()
        if age_ok(policy, profile.age)
        and code_ok(policy, "jobCdNmList", profile.employment)
        and code_ok(policy, "schoolCdNmList", profile.education)
        and region_ok(policy, profile.region, include_nationwide)
        and open_ok(policy, include_closed)
        and query_ok(policy, query)
    ]


def _categories(raw: str | None) -> list[str]:
    seen: list[str] = []
    for value in (raw or "").split(","):
        value = value.strip()
        if value and value not in seen:
            seen.append(value)
    return seen


def _summary(policy: dict, limit: int = 160) -> str:
    body = policy.get("_body") or ""
    match = re.search(r"정책설명:\s*(.+)", body)
    text = " ".join((match.group(1) if match else body).split())
    return text[:limit] + ("…" if len(text) > limit else "")


def _period_label(policy: dict) -> str:
    if policy.get("aplyPrdSeCd") == "0057002" or policy.get("aplyPrdSeCdNm") == "상시":
        return "상시 모집"
    start, end = policy.get("aplyStartYmd"), policy.get("aplyEndYmd")
    return f"{start} – {end}" if start and end else policy.get("aplyPrdSeCdNm") or "기간 미정"


def _days_left(policy: dict) -> int | None:
    try:
        return (date.fromisoformat(policy["aplyEndYmd"]) - date.today()).days
    except (KeyError, TypeError, ValueError):
        return None


def to_policy_card(policy: dict) -> PolicyCard:
    if is_nationwide(policy):
        regions = ["전국"]
    else:
        regions = sorted(
            {SIDO[str(code)[:2]] for code in (policy.get("zipCdList") or []) if str(code)[:2] in SIDO}
        )
    age_label = "나이 무관"
    if policy.get("sprtTrgtAgeLmtYn") == "Y":
        low, high = policy.get("sprtTrgtMinAge"), policy.get("sprtTrgtMaxAge")
        if low and high:
            age_label = f"{low}–{high}세"
    return PolicyCard(
        plcy_no=str(policy.get("plcyNo", "")),
        title=policy.get("plcyNm") or "이름 없는 정책",
        organization=policy.get("operInstCdNm") or policy.get("sprvsnInstCdNm") or "기관 미상",
        categories=_categories(policy.get("lclsfNm")),
        age_label=age_label,
        period_label=_period_label(policy),
        days_left=_days_left(policy),
        status=policy.get("aplyPrdSeCdNm"),
        jobs=policy.get("jobCdNmList") or [],
        schools=policy.get("schoolCdNmList") or [],
        regions=regions,
        summary=_summary(policy),
        apply_url=policy.get("aplyUrlAddr") or policy.get("refUrlAddr1"),
    )


def policy_options() -> dict:
    jobs: set[str] = set()
    schools: set[str] = set()
    for policy in load_policies():
        jobs.update(policy.get("jobCdNmList") or [])
        schools.update(policy.get("schoolCdNmList") or [])
    clean = lambda values: sorted(value for value in values if value and value != ANY_VALUE)
    return {
        "total": len(load_policies()),
        "jobs": clean(jobs),
        "schools": clean(schools),
        "sido": [{"code": code, "name": name} for code, name in sorted(SIDO.items(), key=lambda x: x[1])],
    }


def _tokens(text: str) -> set[str]:
    return {
        word for word in re.findall(r"[가-힣A-Za-z0-9]{2,}", text or "")
        if word not in _STOPWORDS
    }


def _rank(found: list[dict], question: str, size: int) -> tuple[list[tuple[dict, float]], bool]:
    terms = _tokens(question)
    if not terms:
        return [(item, 0.0) for item in found[:size]], False

    def score(policy: dict) -> int:
        title = policy.get("plcyNm") or ""
        body = policy.get("_body") or ""
        return sum(3 for term in terms if term in title) + sum(1 for term in terms if term in body)

    ordered = sorted(found, key=score, reverse=True)[:size]
    best = score(ordered[0]) if ordered else 0
    scale = max(best, 1)
    return [(item, score(item) / scale) for item in ordered], best > 0


def _source(policy: dict, score: float) -> Source:
    card = to_policy_card(policy)
    return Source(
        plcy_no=card.plcy_no,
        title=card.title,
        organization=card.organization,
        category=card.categories[0] if card.categories else "기타",
        apply_url=card.apply_url,
        apply_period=card.period_label,
        snippet=card.summary,
        score=score,
        policy=card,
    )


def search(
    question: str,
    profile: UserProfile,
    *,
    top_k: int = 5,
    mode: SearchMode = SearchMode.HYBRID,
    include_closed: bool = False,
    include_nationwide: bool = False,
    doc_ids: list[str] | None = None,
) -> SearchResult:
    del mode, doc_ids  # 스텁은 검색 모드·첨부 컬렉션을 아직 구분하지 않는다.
    found = filter_policies(
        profile,
        include_closed=include_closed,
        include_nationwide=include_nationwide,
    )
    ranked, relevant = _rank(found, question, top_k)
    sources = [_source(policy, score) for policy, score in ranked]
    return SearchResult(
        sources=sources,
        matched_policies=[source.plcy_no for source in sources],
        matched=len(found),
        total=len(load_policies()),
        relevant=relevant,
    )


def _extractive_answer(result: SearchResult, attachments: str) -> str:
    if attachments:
        return "첨부한 문서를 우선 확인했어요. 문서 내용과 함께 조건에 맞는 정책을 아래에서 살펴보세요."
    names = [source.title for source in result.sources[:3]]
    if not names:
        return "입력한 조건에 맞는 정책을 찾지 못했어요. 조건을 하나씩 지우거나 마감 정책도 함께 확인해보세요."
    return "질문과 관련해 " + ", ".join(f"‘{name}’" for name in names) + "을 먼저 확인해보세요. 아래 카드에서 신청 조건과 기간을 볼 수 있어요."


def answer(
    question: str,
    profile: UserProfile,
    *,
    session_id: str = "",
    attachments: str = "",
    **options,
) -> AnswerResult:
    started = time.perf_counter()
    result = search(
        question,
        profile,
        top_k=int(options.get("top_k", CONTEXT_SIZE)),
        mode=options.get("mode", SearchMode.HYBRID),
        include_closed=bool(options.get("include_closed", False)),
        include_nationwide=bool(options.get("include_nationwide", False)),
        doc_ids=options.get("doc_ids"),
    )

    # 검증된 안전장치: 직접 근거도 첨부 문서도 없으면 생성 모델을 부르지 않는다.
    relevant = result.relevant or bool(attachments)
    text = _extractive_answer(result, attachments) if relevant else (
        "조건에 맞는 정책 중에서는 질문과 직접 관련된 내용을 찾지 못했어요.\n"
        "아래는 같은 조건으로 신청할 수 있는 다른 정책이에요."
    )
    generated = False
    if relevant and os.getenv("RAG_STUB_MODEL", "false").lower() == "true":
        text = _generate_with_qwen(question, profile, result.sources, attachments)
        generated = True

    return AnswerResult(
        answer=text,
        sources=result.sources,
        matched_policies=result.matched_policies,
        session_id=session_id,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        matched=result.matched,
        total=result.total,
        relevant=result.relevant,
        generated=generated,
        used_attachments=bool(attachments),
    )


def _generate_with_qwen(
    question: str, profile: UserProfile, sources: list[Source], attachments: str
) -> str:
    global _bundle
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    if _bundle is None:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        model = AutoModelForCausalLM.from_pretrained(MODEL_ID)
        model.eval()
        _bundle = tokenizer, model
    tokenizer, model = _bundle
    context = "\n".join(
        f"- {source.title} / {source.organization} / {source.snippet}" for source in sources
    )
    prompt = (
        "제공된 근거만 사용해 한국어로 3~5문장으로 답해요. 근거에 없으면 지어내지 마세요.\n"
        f"조건: {profile.model_dump(exclude_none=True)}\n첨부: {attachments[:1800]}\n"
        f"정책:\n{context}\n질문: {question}"
    )
    inputs = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    )
    with torch.no_grad():
        output = model.generate(
            **inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = output[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def stream_answer(
    question: str,
    profile: UserProfile,
    *,
    session_id: str = "",
    attachments: str = "",
    **options,
) -> Iterator[str]:
    result = answer(
        question, profile, session_id=session_id, attachments=attachments, **options
    )
    for token in re.findall(r"\S+\s*", result.answer):
        yield token
