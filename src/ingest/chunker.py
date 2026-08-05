"""정책 레코드를 RAG 검색 본문으로 바꾼다."""

from __future__ import annotations

import json

from src.ingest.collect import _atomic_json
from src.ingest.config import IngestSettings, settings

TEXT_FIELDS = (
    ("정책명", "plcyNm"),
    ("정책설명", "plcyExplnCn"),
    ("지원내용", "plcySprtCn"),
    ("신청기간", "aplyYmd"),
    ("신청방법", "plcyAplyMthdCn"),
    ("추가자격조건", "addAplyQlfcCndCn"),
    ("참여제한대상", "ptcpPrpTrgtCn"),
    ("제출서류", "sbmsnDcmntCn"),
)


def policy_text(policy: dict) -> str:
    lines = []
    for label, field in TEXT_FIELDS:
        value = " ".join(str(policy.get(field) or "").split())
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def build_rag_documents(config: IngestSettings = settings) -> list[dict]:
    policies = json.loads(config.structured_path.read_text(encoding="utf-8"))
    documents = [
        {"plcyNo": str(policy["plcyNo"]), "text": policy_text(policy)}
        for policy in policies
        if policy.get("plcyNo")
    ]
    _atomic_json(config.rag_docs_path, documents)
    return documents


def main() -> None:
    documents = build_rag_documents()
    print(f"청크 생성 완료: {len(documents):,}건 → {settings.rag_docs_path}")


if __name__ == "__main__":
    main()
