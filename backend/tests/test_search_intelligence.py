"""
Unit Tests for Phase 1 SearchIntelligenceEngine
"""

import unittest
from app.engine.search_intelligence import SearchIntelligenceEngine, CandidateSource


class TestSearchIntelligenceEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SearchIntelligenceEngine()

    def test_hybrid_ranking(self):
        query_text = "neural networks deep learning optimization gradient descent"
        query_tokens = query_text.split()
        query_vector = [0.1] * 384

        source_docs = [
            {"document_id": "doc1", "document_name": "Deep Learning Paper", "text": "neural networks deep learning optimization gradient descent algorithm", "vector_similarity": 0.92, "quality_score": 1.0, "freshness_weight": 1.0},
            {"document_id": "doc2", "document_name": "Unrelated Physics Paper", "text": "thermodynamics quantum mechanics entropy heat transfer", "vector_similarity": 0.10, "quality_score": 1.0, "freshness_weight": 1.0},
        ]

        candidates = self.engine.rank_candidates(query_text, query_tokens, query_vector, source_docs)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].source_id, "doc1")
        self.assertGreater(candidates[0].combined_score, candidates[1].combined_score)
        self.assertEqual(candidates[0].explainability["retrieval_mode"], "hybrid_bm25_faiss")


if __name__ == '__main__':
    unittest.main()
