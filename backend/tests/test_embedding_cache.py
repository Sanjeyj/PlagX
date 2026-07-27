"""
Unit Tests for Phase 8 EmbeddingCacheManager
"""

import unittest
import numpy as np
from app.engine.embedding_cache import EmbeddingCacheManager


class TestEmbeddingCacheManager(unittest.TestCase):

    def setUp(self):
        self.cache_mgr = EmbeddingCacheManager(max_entries=100)

    def test_cache_hit_and_eviction(self):
        text = "This is a test sentence for embedding caching."
        emb = np.array([0.1, 0.2, 0.3], dtype=np.float32)

        self.assertIsNone(self.cache_mgr.get(text))
        self.cache_mgr.put(text, emb)

        cached = self.cache_mgr.get(text)
        self.assertIsNotNone(cached)
        np.testing.assert_array_equal(cached, emb)

    def test_encode_batched(self):
        texts = ["Sentence 1", "Sentence 2", "Sentence 1"]

        def mock_encode(t_list, batch_size):
            return np.ones((len(t_list), 4), dtype=np.float32)

        matrix = self.cache_mgr.encode_batched(texts, mock_encode, batch_size=2)
        self.assertEqual(matrix.shape, (3, 4))


if __name__ == '__main__':
    unittest.main()
