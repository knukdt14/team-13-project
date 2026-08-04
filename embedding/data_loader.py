"""정책 검색 문서와 구조화 정책 JSON 로더."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path}")
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as file:
            return [json.loads(line) for line in file if line.strip()]
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"문서 파일의 최상위 값은 배열이어야 합니다: {path}")
    return data


def load_documents(path: Path) -> list[dict[str, Any]]:
    """현재 RAG 문서 또는 전처리 담당자의 청크를 공통 형식으로 바꾼다."""
    records = _read_records(path)
    documents: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        policy_id = str(record.get("policy_id") or record.get("plcyNo") or "").strip()
        text = str(record.get("text") or "").strip()
        if not policy_id or not text:
            continue
        documents.append(
            {
                "chunk_id": str(record.get("chunk_id") or f"{policy_id}_full_{index}"),
                "policy_id": policy_id,
                "section": str(record.get("section") or "full"),
                "text": text,
            }
        )
    if not documents:
        raise ValueError(f"검색 가능한 문서가 없습니다: {path}")
    return documents


def load_policies(path: Path) -> dict[str, dict[str, Any]]:
    records = _read_records(path)
    return {
        str(record["plcyNo"]): record
        for record in records
        if record.get("plcyNo") not in (None, "")
    }
