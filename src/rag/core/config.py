"""임베딩 검색 모듈의 경로와 기본 설정."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


RAG_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = RAG_DIR.parents[1]
load_dotenv(RAG_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    documents_path: Path = PROJECT_DIR / "data" / "policies_rag_docs.json"
    policies_path: Path = PROJECT_DIR / "data" / "policies_structured.json"
    storage_dir: Path = RAG_DIR / "storage"
    model_name: str = os.getenv(
        "EMBEDDING_MODEL",
        "BAAI/bge-m3",
    )
    batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "4"))
    max_seq_length: int = int(os.getenv("EMBEDDING_MAX_SEQ_LENGTH", "1024"))
    device: str = os.getenv("EMBEDDING_DEVICE", "auto")
    use_fp16: bool = os.getenv("EMBEDDING_USE_FP16", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    candidate_k: int = int(os.getenv("EMBEDDING_CANDIDATE_K", "100"))
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "youth_policies_bge_m3")

    @property
    def index_path(self) -> Path:
        return self.storage_dir / "index.faiss"

    @property
    def metadata_path(self) -> Path:
        return self.storage_dir / "chunk_metadata.json"

    @property
    def manifest_path(self) -> Path:
        return self.storage_dir / "manifest.json"

    @property
    def chroma_path(self) -> Path:
        return self.storage_dir / "chroma"


DEFAULT_SETTINGS = Settings()
