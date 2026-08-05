"""백엔드 환경변수 설정."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.shared.paths import APP_DB, CHROMA_DIR, PROJECT_ROOT


@dataclass(frozen=True)
class Settings:
    app_name: str = "청년정책도우미 API"
    db_path: Path = Path(os.getenv("DB_PATH", APP_DB)).resolve()
    chroma_dir: Path = Path(os.getenv("CHROMA_DIR", CHROMA_DIR)).resolve()
    rag_stub: bool = os.getenv("RAG_STUB", "true").lower() == "true"
    frontend_dist: Path = Path(
        os.getenv("FRONTEND_DIST", PROJECT_ROOT / "frontend" / "dist")
    ).resolve()


settings = Settings()
