"""임베딩 모델 실행 장치를 선택하고 검증한다."""

from __future__ import annotations

import torch


def resolve_device(requested: str = "auto") -> str:
    requested = requested.lower().strip()
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(
            "EMBEDDING_DEVICE=cuda로 설정됐지만 현재 PyTorch는 CUDA를 사용할 수 "
                "없습니다. src/rag/.venv-gpu의 Python으로 실행하세요."
        )
    if requested not in {"cpu", "cuda"} and not requested.startswith("cuda:"):
        raise ValueError(f"지원하지 않는 EMBEDDING_DEVICE입니다: {requested}")
    return requested


def describe_device(device: str) -> str:
    if device.startswith("cuda"):
        index = torch.cuda.current_device() if device == "cuda" else int(device.split(":")[1])
        return f"{device} ({torch.cuda.get_device_name(index)})"
    return "cpu"
