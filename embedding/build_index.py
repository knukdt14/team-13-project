"""정책 문서를 임베딩하고 FAISS 코사인 유사도 인덱스를 생성한다."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

try:
    from .config import DEFAULT_SETTINGS
    from .data_loader import load_documents
    from .device import describe_device, resolve_device
except ImportError:  # python embedding/build_index.py 실행도 지원
    from config import DEFAULT_SETTINGS
    from data_loader import load_documents
    from device import describe_device, resolve_device


def build_index(
    documents_path: Path = DEFAULT_SETTINGS.documents_path,
    storage_dir: Path = DEFAULT_SETTINGS.storage_dir,
    model_name: str = DEFAULT_SETTINGS.model_name,
    batch_size: int = DEFAULT_SETTINGS.batch_size,
    max_seq_length: int = DEFAULT_SETTINGS.max_seq_length,
    requested_device: str = DEFAULT_SETTINGS.device,
    use_fp16: bool = DEFAULT_SETTINGS.use_fp16,
    with_chroma: bool = False,
) -> dict[str, object]:
    documents = load_documents(documents_path)
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
                    }
                    for document in batch
                ],
                embeddings=embeddings[start:end].astype(np.float32).tolist(),
            )
        if collection.count() != len(documents):
            raise RuntimeError("Chroma 저장 문서 수가 원본 문서 수와 다릅니다.")

    manifest: dict[str, object] = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "documents_path": str(documents_path.resolve()),
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
    }
    with (storage_dir / "manifest.json").open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
    print(f"인덱스 저장 완료: {storage_dir}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="청년정책 임베딩 인덱스를 생성합니다.")
    parser.add_argument("--documents", type=Path, default=DEFAULT_SETTINGS.documents_path)
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
        args.documents,
        args.storage,
        args.model,
        args.batch_size,
        args.max_seq_length,
        args.device,
        not args.fp32,
        args.with_chroma,
    )


if __name__ == "__main__":
    main()
