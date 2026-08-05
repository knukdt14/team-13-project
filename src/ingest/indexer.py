"""정책 본문과 스칼라 메타데이터를 Chroma에 적재한다."""

from __future__ import annotations

import json
from datetime import date

from src.ingest.config import IngestSettings, settings
from src.shared.constants import ANY_VALUE, NATIONWIDE_MIN_CODES

COLLECTION_NAME = "youth_policies"


def _integer(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_open(policy: dict) -> bool:
    if policy.get("aplyPrdSeCd") == "0057003" or policy.get("aplyPrdSeCdNm") == "마감":
        return False
    if policy.get("aplyPrdSeCd") == "0057002" or policy.get("aplyPrdSeCdNm") == "상시":
        return True
    try:
        return date.fromisoformat(policy.get("aplyEndYmd") or "") >= date.today()
    except ValueError:
        return True


def metadata_for(policy: dict) -> dict[str, str | int | bool]:
    zip_codes = [str(code) for code in policy.get("zipCdList") or []]
    sido_codes = sorted({code[:2] for code in zip_codes if len(code) >= 2})
    jobs = [str(code) for code in policy.get("jobCdList") or []]
    schools = [str(code) for code in policy.get("schoolCdList") or []]
    job_names = policy.get("jobCdNmList") or []
    school_names = policy.get("schoolCdNmList") or []
    categories = []
    for value in str(policy.get("lclsfNm") or "").split(","):
        value = value.strip()
        if value and value not in categories:
            categories.append(value)
    return {
        "plcy_no": str(policy.get("plcyNo") or ""),
        "title": str(policy.get("plcyNm") or ""),
        "organization": str(policy.get("operInstCdNm") or policy.get("sprvsnInstCdNm") or ""),
        "category": ",".join(categories),
        "age_min": _integer(policy.get("sprtTrgtMinAge")),
        "age_max": _integer(policy.get("sprtTrgtMaxAge"), 120),
        "age_unlimited": policy.get("sprtTrgtAgeLmtYn") != "Y",
        "sido_codes": ",".join(sido_codes),
        "is_nationwide": len(zip_codes) >= NATIONWIDE_MIN_CODES,
        "job_codes": ",".join(jobs),
        "school_codes": ",".join(schools),
        "job_any": ANY_VALUE in job_names or "0013010" in jobs,
        "school_any": ANY_VALUE in school_names or "0049010" in schools,
        "apply_start": str(policy.get("aplyStartYmd") or ""),
        "apply_end": str(policy.get("aplyEndYmd") or ""),
        "is_open": _is_open(policy),
        "apply_url": str(policy.get("aplyUrlAddr") or policy.get("refUrlAddr1") or ""),
    }


def index_policies(config: IngestSettings = settings, *, batch_size: int = 100) -> int:
    try:
        import chromadb
    except ImportError as error:
        raise RuntimeError("Chroma 적재에는 chromadb 패키지가 필요합니다.") from error

    policies = json.loads(config.structured_path.read_text(encoding="utf-8"))
    docs = json.loads(config.rag_docs_path.read_text(encoding="utf-8"))
    text_by_id = {str(item["plcyNo"]): item.get("text", "") for item in docs}
    client = chromadb.PersistentClient(path=str(config.chroma_dir))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:  # 컬렉션이 처음이면 삭제할 것이 없다.
        pass
    collection = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    rows = [policy for policy in policies if str(policy.get("plcyNo") or "") in text_by_id]
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        collection.add(
            ids=[str(item["plcyNo"]) for item in batch],
            documents=[text_by_id[str(item["plcyNo"])] for item in batch],
            metadatas=[metadata_for(item) for item in batch],
        )
    return len(rows)


def main() -> None:
    count = index_policies()
    print(f"Chroma 적재 완료: {count:,}건 → {settings.chroma_dir}")


if __name__ == "__main__":
    main()
