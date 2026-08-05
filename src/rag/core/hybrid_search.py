"""정책 문서의 BM25 검색과 Dense·BM25 순위를 결합한다."""

from __future__ import annotations

import re
from typing import Sequence

import numpy as np
from rank_bm25 import BM25Okapi


TOKEN_PATTERN = re.compile(r"[가-힣]+|[A-Za-z]+|\d+")


def tokenize(text: str) -> list[str]:
    """형태소 분석기 없이 단어와 한국어 2-gram을 함께 만든다."""
    words = [token.lower() for token in TOKEN_PATTERN.findall(text)]
    bigrams: list[str] = []
    for word in words:
        if re.fullmatch(r"[가-힣]+", word) and len(word) >= 2:
            bigrams.extend(word[index : index + 2] for index in range(len(word) - 1))
    return words + bigrams


class BM25Search:
    def __init__(self, texts: Sequence[str]):
        self.corpus = [tokenize(text) for text in texts]
        self.index = BM25Okapi(self.corpus)

    def rank(self, query: str) -> tuple[np.ndarray, np.ndarray]:
        scores = np.asarray(self.index.get_scores(tokenize(query)), dtype=np.float32)
        indices = np.argsort(-scores)
        return indices, scores[indices]


def reciprocal_rank_fusion(
    dense_indices: Sequence[int],
    bm25_indices: Sequence[int],
    dense_weight: float = 0.6,
    bm25_weight: float = 0.4,
    rank_constant: int = 60,
) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for rank, index in enumerate(dense_indices, start=1):
        scores[int(index)] = scores.get(int(index), 0.0) + dense_weight / (
            rank_constant + rank
        )
    for rank, index in enumerate(bm25_indices, start=1):
        scores[int(index)] = scores.get(int(index), 0.0) + bm25_weight / (
            rank_constant + rank
        )
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)
