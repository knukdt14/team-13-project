"""저장소 기준 경로. 환경변수로 운영 경로를 바꿀 수 있다."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data")).resolve()
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", PROJECT_ROOT / "chroma_db")).resolve()
APP_DB = Path(os.getenv("DB_PATH", PROJECT_ROOT / "app.db")).resolve()

RAW_POLICIES = DATA_DIR / "youth_policies_raw.json"
STRUCTURED_POLICIES = DATA_DIR / "policies_structured.json"
RAG_DOCUMENTS = DATA_DIR / "policies_rag_docs.json"
CODE_DEFINITIONS = DATA_DIR / "code_definitions.json"
PROVINCES_GEOJSON = DATA_DIR / "provinces.geojson"
