"""질문을 입력받아 조건에 맞는 청년정책 Top-K를 반환한다."""

from __future__ import annotations

import json
from typing import Any, Mapping

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .core.config import DEFAULT_SETTINGS, Settings
from .core.data_loader import load_policies
from .core.device import resolve_device
from .core.hybrid_search import BM25Search, reciprocal_rank_fusion
from .eligibility import ConditionExtractor, PolicyFilter


class PolicyRetriever:
    """백엔드가 직접 호출할 정책 검색 인터페이스."""

    def __init__(self, settings: Settings = DEFAULT_SETTINGS):
        self.settings = settings
        self._validate_index_files()
        with settings.manifest_path.open("r", encoding="utf-8") as file:
            self.manifest = json.load(file)
        indexed_model = str(self.manifest.get("model_name", ""))
        if indexed_model != settings.model_name:
            raise RuntimeError(
                f"현재 인덱스 모델({indexed_model})과 설정 모델({settings.model_name})이 "
                "다릅니다. python -m src.rag.cli.build_index 를 다시 실행하세요."
            )
        with settings.metadata_path.open("r", encoding="utf-8") as file:
            self.documents: list[dict[str, Any]] = json.load(file)

        self.policies = load_policies(settings.policies_path)
        # Windows용 FAISS의 한글 경로 제약을 피하기 위해 Python으로 파일을 읽는다.
        with settings.index_path.open("rb") as file:
            serialized_index = np.frombuffer(file.read(), dtype=np.uint8)
        self.index = faiss.deserialize_index(serialized_index)
        if self.index.ntotal != len(self.documents):
            raise RuntimeError("FAISS 인덱스와 청크 메타데이터 개수가 다릅니다. 인덱스를 다시 생성하세요.")
        self.device = resolve_device(settings.device)
        self.model = SentenceTransformer(
            str(self.manifest["model_name"]), device=self.device
        )
        self.model.max_seq_length = int(
            self.manifest.get("max_seq_length", settings.max_seq_length)
        )
        if self.device.startswith("cuda") and settings.use_fp16:
            self.model.half()
        self.bm25 = BM25Search([document["text"] for document in self.documents])
        self.extractor = ConditionExtractor()
        self.policy_filter = PolicyFilter()

    def search(
        self,
        question: str,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
        include_closed: bool = False,
        mode: str = "hybrid",
    ) -> dict[str, Any]:
        """조건 추출, 필터링, 검색 후 중복 없는 정책 Top-K를 반환한다.

        filters는 자동 추출값을 덮어쓴다. 지원 필드는 age, region,
        employment, education, income_bracket, marriage, category이다.
        이전 이름인 job_status와 school_status도 호환한다.
        """
        if top_k < 1:
            raise ValueError("top_k는 1 이상이어야 합니다.")
        if mode not in {"vector", "bm25", "hybrid"}:
            raise ValueError("mode는 vector, bm25, hybrid 중 하나여야 합니다.")
        extracted, search_text = self.extractor.extract(question)
        conditions = extracted.to_dict()
        if filters:
            supplied = {key: value for key, value in filters.items() if value is not None}
            if "job_status" in supplied and "employment" not in supplied:
                supplied["employment"] = supplied.pop("job_status")
            if "school_status" in supplied and "education" not in supplied:
                supplied["education"] = supplied.pop("school_status")
            conditions.update(supplied)

        query_vector = self.model.encode(
            [search_text], convert_to_numpy=True, normalize_embeddings=True
        ).astype(np.float32)
        policies = self._ranked_search(
            query_vector,
            search_text,
            conditions,
            top_k,
            include_closed,
            mode,
        )
        return {
            "question": question,
            "search_text": search_text,
            "extracted_conditions": conditions,
            "top_k": top_k,
            "result_count": len(policies),
            "search_mode": mode,
            "policies": policies,
        }

    def _ranked_search(
        self,
        query_vector: np.ndarray,
        search_text: str,
        conditions: Mapping[str, Any],
        top_k: int,
        include_closed: bool,
        mode: str,
    ) -> list[dict[str, Any]]:
        dense_indices, dense_values = self._dense_ranking(query_vector)
        bm25_indices, bm25_values = self.bm25.rank(search_text)
        dense_score_by_index = {
            int(index): float(score) for index, score in zip(dense_indices, dense_values)
        }
        bm25_score_by_index = {
            int(index): float(score) for index, score in zip(bm25_indices, bm25_values)
        }

        if mode == "vector":
            ranked = list(zip(dense_indices.tolist(), dense_values.tolist()))
        elif mode == "bm25":
            maximum = float(bm25_values[0]) if len(bm25_values) and bm25_values[0] > 0 else 1.0
            ranked = [
                (int(index), float(score) / maximum)
                for index, score in zip(bm25_indices, bm25_values)
            ]
        else:
            fused = reciprocal_rank_fusion(dense_indices, bm25_indices)
            maximum = fused[0][1] if fused else 1.0
            ranked = [(index, score / maximum) for index, score in fused]

        results: list[dict[str, Any]] = []
        seen_policy_ids: set[str] = set()
        for index, score in ranked:
            chunk = self.documents[int(index)]
            policy_id = str(chunk["policy_id"])
            if policy_id in seen_policy_ids:
                continue
            policy = self.policies.get(policy_id)
            if not policy or not self.policy_filter.matches(policy, conditions, include_closed):
                continue
            seen_policy_ids.add(policy_id)
            results.append(
                self._format_result(
                    policy,
                    chunk,
                    float(score),
                    mode=mode,
                    dense_score=dense_score_by_index.get(int(index)),
                    bm25_score=bm25_score_by_index.get(int(index)),
                )
            )
            if len(results) >= top_k:
                break
        return results

    def _dense_ranking(self, query_vector: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        scores, indices = self.index.search(query_vector, len(self.documents))
        return indices[0].astype(np.int64), scores[0].astype(np.float32)

    def _search_unique_policies(
        self,
        query_vector: np.ndarray,
        conditions: Mapping[str, Any],
        top_k: int,
        include_closed: bool,
    ) -> list[dict[str, Any]]:
        total = int(self.index.ntotal)
        search_k = min(total, max(self.settings.candidate_k, top_k * 10))
        while True:
            scores, indices = self.index.search(query_vector, search_k)
            results = self._collect_results(
                scores[0], indices[0], conditions, top_k, include_closed
            )
            if len(results) >= top_k or search_k >= total:
                return results
            search_k = min(total, search_k * 2)

    def _collect_results(
        self,
        scores: np.ndarray,
        indices: np.ndarray,
        conditions: Mapping[str, Any],
        top_k: int,
        include_closed: bool,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        seen_policy_ids: set[str] = set()
        for score, index in zip(scores, indices):
            if int(index) < 0:
                continue
            chunk = self.documents[int(index)]
            policy_id = str(chunk["policy_id"])
            if policy_id in seen_policy_ids:
                continue
            policy = self.policies.get(policy_id)
            if not policy or not self.policy_filter.matches(policy, conditions, include_closed):
                continue
            seen_policy_ids.add(policy_id)
            results.append(self._format_result(policy, chunk, float(score)))
            if len(results) >= top_k:
                break
        return results

    def _format_result(
        self,
        policy: Mapping[str, Any],
        chunk: Mapping[str, Any],
        score: float,
        mode: str = "vector",
        dense_score: float | None = None,
        bm25_score: float | None = None,
    ) -> dict[str, Any]:
        return {
            "policy_id": str(policy.get("plcyNo")),
            "policy_name": policy.get("plcyNm"),
            "score": round(score, 6),
            "retrieval_mode": mode,
            "dense_score": round(dense_score, 6) if dense_score is not None else None,
            "bm25_score": round(bm25_score, 6) if bm25_score is not None else None,
            "matched_chunk_id": chunk.get("chunk_id"),
            "matched_section": chunk.get("section"),
            "matched_text": chunk.get("text"),
            "metadata": {
                "large_category": policy.get("lclsfNm"),
                "middle_category": policy.get("mclsfNm"),
                "keywords": policy.get("plcyKywdNm"),
                "min_age": policy.get("sprtTrgtMinAge"),
                "max_age": policy.get("sprtTrgtMaxAge"),
                "age_limited": policy.get("sprtTrgtAgeLmtYn") == "Y",
                "job_statuses": policy.get("jobCdNmList") or [],
                "school_statuses": policy.get("schoolCdNmList") or [],
                "income_condition": policy.get("earnCndSeCdNm"),
                "income_min": policy.get("earnMinAmt"),
                "income_max": policy.get("earnMaxAmt"),
                "income_details": policy.get("earnEtcCn"),
                "application_type": policy.get("aplyPrdSeCdNm"),
                "application_start": policy.get("aplyStartYmd"),
                "application_end": policy.get("aplyEndYmd"),
                "is_open": self.policy_filter.is_open(policy),
                "organization": policy.get("operInstCdNm") or policy.get("rgtrInstCdNm"),
                "application_url": policy.get("aplyUrlAddr"),
                "reference_url": policy.get("refUrlAddr1") or policy.get("refUrlAddr2"),
            },
        }

    def _validate_index_files(self) -> None:
        missing = [
            path
            for path in (
                self.settings.index_path,
                self.settings.metadata_path,
                self.settings.manifest_path,
            )
            if not path.exists()
        ]
        if missing:
            raise FileNotFoundError(
                "임베딩 인덱스가 없습니다. 먼저 python -m src.rag.cli.build_index 를 "
                "실행하세요. 누락 파일: " + ", ".join(str(path) for path in missing)
            )
