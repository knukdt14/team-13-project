"""``python -m src.ingest.cli`` 명령 진입점."""

from __future__ import annotations

import argparse

from src.ingest.chunker import build_rag_documents
from src.ingest.collect import collect_policies
from src.ingest.indexer import index_policies
from src.ingest.normalize import normalize_policies
from src.ingest.regions.geojson import simplify_geojson


def run(command: str) -> None:
    actions = {
        "collect": collect_policies,
        "normalize": normalize_policies,
        "chunk": build_rag_documents,
        "index": index_policies,
        "geo": simplify_geojson,
    }
    if command == "all":
        for name in ("collect", "normalize", "chunk", "index", "geo"):
            print(f"[{name}]")
            actions[name]()
        return
    actions[command]()


def main() -> None:
    parser = argparse.ArgumentParser(description="청년정책 수집·인덱싱 파이프라인")
    parser.add_argument("command", choices=("collect", "normalize", "chunk", "index", "geo", "all"))
    run(parser.parse_args().command)


if __name__ == "__main__":
    main()
