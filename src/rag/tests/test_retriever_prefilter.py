import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from src.rag.eligibility import ConditionExtractor, PolicyFilter
from src.rag.retriever import PolicyRetriever


def _policy(policy_id: str, minimum: str, maximum: str, flag: str = "N"):
    return {
        "plcyNo": policy_id,
        "plcyNm": policy_id,
        "sprtTrgtAgeLmtYn": flag,
        "sprtTrgtMinAge": minimum,
        "sprtTrgtMaxAge": maximum,
    }


class RetrieverPrefilterTest(unittest.TestCase):
    def setUp(self):
        self.retriever = PolicyRetriever.__new__(PolicyRetriever)
        self.retriever.policies = {
            "too_old": _policy("too_old", "29", "39"),
            "eligible": _policy("eligible", "19", "34"),
            "unlimited": _policy("unlimited", "0", "0", flag="Y"),
        }
        self.retriever.documents = [
            {"policy_id": "too_old", "text": "가장 비슷한 정책"},
            {"policy_id": "eligible", "text": "신청 가능한 정책"},
            {"policy_id": "unlimited", "text": "연령 제한 없는 정책"},
        ]
        self.retriever.policy_filter = PolicyFilter(today=date(2026, 8, 5))

    def test_structured_filter_selects_documents_before_ranking(self):
        indices = self.retriever._prefilter_document_indices(
            {"age": 25}, include_closed=True
        )
        self.assertEqual(indices.tolist(), [1, 2])

    def test_search_passes_only_eligible_candidates_to_ranking(self):
        self.retriever.extractor = ConditionExtractor()
        self.retriever.model = Mock()
        self.retriever.model.encode.return_value = np.asarray(
            [[1.0, 0.0]], dtype=np.float32
        )
        self.retriever._ranked_search = Mock(return_value=[])

        self.retriever.search("25살 청년에게 맞는 정책", include_closed=True)

        candidate_indices = self.retriever._ranked_search.call_args.args[2]
        self.assertEqual(candidate_indices.tolist(), [1, 2])

    def test_search_skips_embedding_when_no_policy_is_eligible(self):
        self.retriever.policies = {
            "too_old": self.retriever.policies["too_old"]
        }
        self.retriever.documents = [self.retriever.documents[0]]
        self.retriever.extractor = ConditionExtractor()
        self.retriever.model = Mock()
        self.retriever._ranked_search = Mock(return_value=[])

        result = self.retriever.search(
            "25살 청년에게 맞는 정책", include_closed=True
        )

        self.assertEqual(result["policies"], [])
        self.retriever.model.encode.assert_not_called()
        self.retriever._ranked_search.assert_not_called()

    def test_dense_ranking_compares_only_candidate_vectors(self):
        self.retriever.index = SimpleNamespace(d=2)
        self.retriever.document_embeddings = np.asarray(
            [[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]], dtype=np.float32
        )
        indices, scores = self.retriever._dense_ranking(
            np.asarray([[1.0, 0.0]], dtype=np.float32),
            np.asarray([1, 2], dtype=np.int64),
        )
        self.assertEqual(indices.tolist(), [1, 2])
        self.assertAlmostEqual(float(scores[0]), 0.8, places=6)


if __name__ == "__main__":
    unittest.main()
