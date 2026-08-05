"""터미널에서 검색 파이프라인을 확인하는 실행 파일."""

import argparse
import json
from pathlib import Path
import sys

try:
    from ..retriever import PolicyRetriever
except ImportError:  # python src/rag/cli/search_cli.py 직접 실행도 지원
    project_dir = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_dir))
    from src.rag.retriever import PolicyRetriever


def main() -> None:
    parser = argparse.ArgumentParser(description="청년정책 Top-K 검색")
    parser.add_argument("question", help="예: 대구에 사는 28살 미취업자 지원 정책")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--include-closed", action="store_true")
    parser.add_argument(
        "--mode", choices=("vector", "bm25", "hybrid"), default="hybrid"
    )
    args = parser.parse_args()
    result = PolicyRetriever().search(
        args.question,
        top_k=args.top_k,
        include_closed=args.include_closed,
        mode=args.mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
