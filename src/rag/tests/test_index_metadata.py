import unittest

from src.rag.cli.build_index import (
    NATIONWIDE_MIN_ZIP_CODE_COUNT,
    add_region_metadata,
    region_metadata,
)


class IndexMetadataTest(unittest.TestCase):
    def test_extracts_unique_sido_codes(self):
        metadata = region_metadata(
            {"zipCdList": ["27110", "27140", "41110"]}
        )
        self.assertEqual(metadata["region_codes"], ["27", "41"])
        self.assertFalse(metadata["is_nationwide"])

    def test_detects_nationwide_policy(self):
        metadata = region_metadata(
            {
                "zipCdList": [
                    f"27{number:03d}"
                    for number in range(NATIONWIDE_MIN_ZIP_CODE_COUNT)
                ]
            }
        )
        self.assertTrue(metadata["is_nationwide"])

    def test_199_region_codes_are_not_nationwide(self):
        metadata = region_metadata(
            {
                "zipCdList": [
                    f"27{number:03d}"
                    for number in range(NATIONWIDE_MIN_ZIP_CODE_COUNT - 1)
                ]
            }
        )
        self.assertFalse(metadata["is_nationwide"])

    def test_joins_structured_policy_by_policy_id(self):
        documents = [
            {
                "chunk_id": "P001_full_0",
                "policy_id": "P001",
                "section": "full",
                "text": "정책 설명",
            }
        ]
        policies = {"P001": {"zipCdList": ["27110"]}}
        enriched = add_region_metadata(documents, policies)
        self.assertEqual(enriched[0]["region_codes"], ["27"])
        self.assertFalse(enriched[0]["is_nationwide"])


if __name__ == "__main__":
    unittest.main()
