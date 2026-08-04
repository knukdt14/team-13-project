import unittest

from embedding.hybrid_search import BM25Search, reciprocal_rank_fusion, tokenize


class HybridSearchTest(unittest.TestCase):
    def test_korean_tokenizer_adds_bigrams(self):
        tokens = tokenize("청년 월세지원")
        self.assertIn("청년", tokens)
        self.assertIn("월세", tokens)

    def test_bm25_ranks_matching_document_first(self):
        search = BM25Search(["청년 월세 주거비 지원", "청년 취업 면접 지원"])
        indices, _ = search.rank("월세 주거 지원")
        self.assertEqual(int(indices[0]), 0)

    def test_rrf_combines_two_rankings(self):
        ranked = reciprocal_rank_fusion([0, 1, 2], [1, 0, 2])
        self.assertIn(ranked[0][0], {0, 1})
        self.assertGreater(ranked[0][1], ranked[-1][1])


if __name__ == "__main__":
    unittest.main()
