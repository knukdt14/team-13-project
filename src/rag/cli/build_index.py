"""정책 문서를 임베딩하고 FAISS 코사인 유사도 인덱스를 생성한다."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

try:
    from ..core.config import DEFAULT_SETTINGS, PROJECT_DIR
    from ..core.data_loader import load_documents, load_policies
    from ..core.device import describe_device, resolve_device
except ImportError:  # python src/rag/cli/build_index.py 직접 실행도 지원
    project_dir = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_dir))
    from src.rag.core.config import DEFAULT_SETTINGS, PROJECT_DIR
    from src.rag.core.data_loader import load_documents, load_policies
    from src.rag.core.device import describe_device, resolve_device


NATIONWIDE_MIN_ZIP_CODE_COUNT = 200


def region_metadata(policy: Mapping[str, Any]) -> dict[str, object]:
    """zipCdList의 시도 코드와 전국 정책 여부를 검색 메타데이터로 만든다."""
    raw_codes = policy.get("zipCdList") or policy.get("zipCd") or []
    if isinstance(raw_codes, str):
        raw_codes = [part.strip() for part in raw_codes.split(",")]
    zip_codes = {
        str(code).strip()
        for code in raw_codes
        if code not in (None, "") and len(str(code).strip()) >= 2
    }
    region_codes = sorted(
        {code[:2] for code in zip_codes}
    )
    return {
        "region_codes": region_codes,
        "is_nationwide": len(zip_codes) >= NATIONWIDE_MIN_ZIP_CODE_COUNT,
    }


def add_region_metadata(
    documents: list[dict[str, Any]],
    policies: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """문서의 policy_id로 structured 정책을 연결해 지역 메타데이터를 붙인다."""
    enriched: list[dict[str, Any]] = []
    missing_policy_ids: set[str] = set()
    for document in documents:
        policy_id = str(document["policy_id"])
        policy = policies.get(policy_id)
        item = dict(document)
        if policy is None:
            missing_policy_ids.add(policy_id)
            item.update({"region_codes": [], "is_nationwide": False})
        else:
            item.update(region_metadata(policy))
        enriched.append(item)
    if missing_policy_ids:
        sample = ", ".join(sorted(missing_policy_ids)[:5])
        print(
            f"경고: structured 정책을 찾지 못한 policy_id {len(missing_policy_ids):,}개 "
            f"(예: {sample})"
        )
    return enriched


def build_index(
    documents_path: Path = DEFAULT_SETTINGS.documents_path,
    storage_dir: Path = DEFAULT_SETTINGS.storage_dir,
    model_name: str = DEFAULT_SETTINGS.model_name,
    batch_size: int = DEFAULT_SETTINGS.batch_size,
    max_seq_length: int = DEFAULT_SETTINGS.max_seq_length,
    requested_device: str = DEFAULT_SETTINGS.device,
    use_fp16: bool = DEFAULT_SETTINGS.use_fp16,
    with_chroma: bool = False,
    policies_path: Path = DEFAULT_SETTINGS.policies_path,
) -> dict[str, object]:
    documents = load_documents(documents_path)
    policies = load_policies(policies_path)
    documents = add_region_metadata(documents, policies)
    storage_dir.mkdir(parents=True, exist_ok=True)
    print(f"문서 {len(documents):,}개를 불러왔습니다.")
    device = resolve_device(requested_device)
    print(f"임베딩 모델: {model_name}")
    print(f"실행 장치: {describe_device(device)}")

    model = SentenceTransformer(model_name, device=device)
    model.max_seq_length = max_seq_length
    if device.startswith("cuda") and use_fp16:
        model.half()
    embeddings = model.encode(
        [document["text"] for document in documents],
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    # Windows용 FAISS는 한글 경로를 직접 열지 못하므로 Python 파일 API를 쓴다.
    serialized_index = faiss.serialize_index(index)
    with (storage_dir / "index.faiss").open("wb") as file:
        file.write(serialized_index.tobytes())
    with (storage_dir / "chunk_metadata.json").open("w", encoding="utf-8") as file:
        json.dump(documents, file, ensure_ascii=False)

    if with_chroma:
        import chromadb

        chroma_path = storage_dir / "chroma"
        if chroma_path.exists():
            shutil.rmtree(chroma_path)
        chroma_client = chromadb.PersistentClient(path=str(chroma_path))
        collection = chroma_client.create_collection(
            name=DEFAULT_SETTINGS.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        upsert_batch_size = 128
        for start in range(0, len(documents), upsert_batch_size):
            end = min(start + upsert_batch_size, len(documents))
            batch = documents[start:end]
            collection.upsert(
                ids=[document["chunk_id"] for document in batch],
                documents=[document["text"] for document in batch],
                metadatas=[
                    {
                        "policy_id": document["policy_id"],
                        "section": document["section"],
                        "region_codes": ",".join(document["region_codes"]),
                        "is_nationwide": document["is_nationwide"],
                    }
                    for document in batch
                ],
                embeddings=embeddings[start:end].astype(np.float32).tolist(),
            )
        if collection.count() != len(documents):
            raise RuntimeError("Chroma 저장 문서 수가 원본 문서 수와 다릅니다.")

    manifest: dict[str, object] = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "documents_path": _manifest_path(documents_path),
        "policies_path": _manifest_path(policies_path),
        "document_count": len(documents),
        "model_name": model_name,
        "embedding_dimension": int(embeddings.shape[1]),
        "max_seq_length": max_seq_length,
        "build_device": describe_device(device),
        "dtype": "float16" if device.startswith("cuda") and use_fp16 else "float32",
        "similarity": "cosine",
        "normalized": True,
        "vector_db": "faiss+chroma" if with_chroma else "faiss",
        "chroma_collection": DEFAULT_SETTINGS.chroma_collection if with_chroma else None,
        "metadata_fields": [
            "chunk_id",
            "policy_id",
            "section",
            "region_codes",
            "is_nationwide",
        ],
        "nationwide_min_zip_code_count": NATIONWIDE_MIN_ZIP_CODE_COUNT,
    }
    with (storage_dir / "manifest.json").open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
    print(f"인덱스 저장 완료: {storage_dir}")
    return manifest


def _manifest_path(path: Path) -> str:
    """프로젝트 내부 데이터 경로는 PC와 무관한 상대경로로 기록한다."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_DIR.resolve()).as_posix()
    except ValueError:
        return path.name


def main() -> None:
    parser = argparse.ArgumentParser(description="청년정책 임베딩 인덱스를 생성합니다.")
    parser.add_argument("--documents", type=Path, default=DEFAULT_SETTINGS.documents_path)
    parser.add_argument("--policies", type=Path, default=DEFAULT_SETTINGS.policies_path)
    parser.add_argument("--storage", type=Path, default=DEFAULT_SETTINGS.storage_dir)
    parser.add_argument("--model", default=DEFAULT_SETTINGS.model_name)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_SETTINGS.batch_size)
    parser.add_argument(
        "--max-seq-length", type=int, default=DEFAULT_SETTINGS.max_seq_length
    )
    parser.add_argument("--device", default=DEFAULT_SETTINGS.device)
    parser.add_argument(
        "--fp32", action="store_true", help="GPU에서도 FP32를 사용합니다."
    )
    parser.add_argument(
        "--with-chroma",
        action="store_true",
        help="실험용 Chroma 컬렉션도 함께 생성합니다.",
    )
    args = parser.parse_args()
    build_index(
        documents_path=args.documents,
        storage_dir=args.storage,
        model_name=args.model,
        batch_size=args.batch_size,
        max_seq_length=args.max_seq_length,
        requested_device=args.device,
        use_fp16=not args.fp32,
        with_chroma=args.with_chroma,
        policies_path=args.policies,
    )


if __name__ == "__main__":
    main()
