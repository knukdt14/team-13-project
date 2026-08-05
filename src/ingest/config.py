"""수집 파이프라인 환경 설정."""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.shared.paths import (
    CHROMA_DIR,
    CODE_DEFINITIONS,
    PROVINCES_GEOJSON,
    RAG_DOCUMENTS,
    RAW_POLICIES,
    STRUCTURED_POLICIES,
)


@dataclass(frozen=True)
class IngestSettings:
    api_url: str = os.getenv(
        "ONTONG_API_URL", "https://www.youthcenter.go.kr/opi/youthPlcyList.do"
    )
    api_key: str = os.getenv("ONTONG_API_KEY", "")
    page_size: int = int(os.getenv("ONTONG_PAGE_SIZE", "100"))
    timeout_seconds: int = int(os.getenv("ONTONG_TIMEOUT", "30"))
    raw_path = RAW_POLICIES
    structured_path = STRUCTURED_POLICIES
    rag_docs_path = RAG_DOCUMENTS
    code_definitions_path = CODE_DEFINITIONS
    chroma_dir = CHROMA_DIR
    provinces_path = PROVINCES_GEOJSON


settings = IngestSettings()
