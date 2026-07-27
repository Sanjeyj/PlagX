"""
Unit Tests for Phase 1 Engine Bug Fixes in ExactMatchEngine
"""

import unittest
from app.engine.exact_match import ExactMatchEngine, ExactMatch
from app.engine.config import ExactMatchConfig


class TestExactMatchEnginePhase1(unittest.TestCase):

    def setUp(self):
        config = ExactMatchConfig(min_ngram=3, min_match_words=3, merge_gap=1, whitelist_filter=False)
        self.engine = ExactMatchEngine(config=config)

    def test_merge_adjacent_full_text_reconstruction(self):
        """Test that _merge_adjacent reconstructs matched_text across the complete merged region."""
        query_words = "The quick brown fox jumps over the lazy dog in the forest".split()
        
        match1 = ExactMatch(
            query_start=0, query_end=4,
            source_start=0, source_end=4,
            matched_text="The quick brown fox",
            ngram_size=4,
            source_id="src1", source_name="Source 1"
        )
        match2 = ExactMatch(
            query_start=3, query_end=7,
            source_start=3, source_end=7,
            matched_text="fox jumps over the",
            ngram_size=4,
            source_id="src1", source_name="Source 1"
        )
        
        merged = self.engine._merge_adjacent([match1, match2], query_words)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].query_start, 0)
        self.assertEqual(merged[0].query_end, 7)
        self.assertEqual(merged[0].ngram_size, 7)
        self.assertEqual(merged[0].matched_text, "The quick brown fox jumps over the")

    def test_extend_matches_recovers_longest_region(self):
        """Test that _extend_matches recovers the longest contiguous region without skipping."""
        query_words = "Deep learning models are trained using gradient descent optimization".split()
        source_words = "Deep learning models are trained using gradient descent optimization and backpropagation".split()

        matches = self.engine.find_matches(query_words, source_words, source_id="src1", source_name="Source 1")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].ngram_size, len(query_words))
        self.assertEqual(matches[0].matched_text, " ".join(query_words))

    def test_calculate_exact_score_unique_coverage(self):
        """Test unique token coverage calculation."""
        matches = [
            ExactMatch(0, 5, 0, 5, "a b c d e", 5, "s1", "S1"),
            ExactMatch(3, 8, 3, 8, "d e f g h", 5, "s1", "S1"),
        ]
        score = self.engine.calculate_exact_score(matches, total_words=10)
        self.assertEqual(score, 80.0)  # 8 unique tokens out of 10 = 80.0%


if __name__ == '__main__':
    unittest.main()
