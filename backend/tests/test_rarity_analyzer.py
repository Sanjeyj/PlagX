"""
Unit Tests for Phase 6 RarityAnalyzer
"""

import unittest
from app.engine.rarity_analyzer import RarityAnalyzer


class TestRarityAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = RarityAnalyzer()

    def test_common_transition_suppression(self):
        text = "In this paper we present a novel algorithm."
        rarity = self.analyzer.compute_phrase_rarity(text)
        self.assertLessEqual(rarity, 0.3)

    def test_rare_technical_phrase_boost(self):
        text = "Convolutional backpropagation vector quantization optimization"
        rarity = self.analyzer.compute_phrase_rarity(text)
        self.assertGreaterEqual(rarity, 1.0)


if __name__ == '__main__':
    unittest.main()
