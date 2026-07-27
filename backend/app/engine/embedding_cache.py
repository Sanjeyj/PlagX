"""
Embedding Cache and Large Document Streaming Manager v3.0
Caches vector embeddings and streams large documents (100+ pages) in memory-efficient batches.
"""

import hashlib
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EmbeddingCacheManager:
    """
    LRU Memory Cache for sentence-transformer embeddings.
    Prevents redundant vector encoding operations.
    """

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.cache: Dict[str, np.ndarray] = {}

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def get(self, text: str) -> Optional[np.ndarray]:
        h = self._hash_text(text)
        return self.cache.get(h)

    def put(self, text: str, embedding: np.ndarray):
        if len(self.cache) >= self.max_entries:
            # Evict first 1000 entries
            keys_to_remove = list(self.cache.keys())[:1000]
            for k in keys_to_remove:
                del self.cache[k]
        h = self._hash_text(text)
        self.cache[h] = embedding

    def encode_batched(self, texts: List[str], encode_fn, batch_size: int = 64) -> np.ndarray:
        """Encode texts with caching in memory-efficient batches for 100+ page documents."""
        if not texts:
            return np.array([])

        cached_results: Dict[int, np.ndarray] = {}
        missing_texts: List[str] = []
        missing_indices: List[int] = []

        for idx, text in enumerate(texts):
            emb = self.get(text)
            if emb is not None:
                cached_results[idx] = emb
            else:
                missing_texts.append(text)
                missing_indices.append(idx)

        if missing_texts:
            logger.info(f"Encoding {len(missing_texts)} uncached chunks in batches of {batch_size}...")
            new_embeddings = encode_fn(missing_texts, batch_size=batch_size)
            for i, idx in enumerate(missing_indices):
                emb = new_embeddings[i]
                self.put(missing_texts[i], emb)
                cached_results[idx] = emb

        # Assemble final matrix
        dim = list(cached_results.values())[0].shape[0]
        final_matrix = np.zeros((len(texts), dim), dtype=np.float32)
        for idx in range(len(texts)):
            final_matrix[idx] = cached_results[idx]

        return final_matrix
