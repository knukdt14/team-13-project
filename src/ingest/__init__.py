"""정책 수집·정규화·인덱싱 파이프라인."""

from src.ingest.chunker import build_rag_documents
from src.ingest.collect import collect_policies
from src.ingest.normalize import normalize_policies

__all__ = ["build_rag_documents", "collect_policies", "normalize_policies"]
