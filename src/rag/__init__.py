"""청년정책 RAG(조건 추출, 검색, Solar 생성) 패키지."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .retriever import PolicyRetriever

__all__ = ["PolicyRetriever"]


def __getattr__(name: str) -> Any:
    """공개 검색기를 실제 사용 시점에 불러와 패키지 import를 가볍게 유지한다."""
    if name == "PolicyRetriever":
        from .retriever import PolicyRetriever

        return PolicyRetriever
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
