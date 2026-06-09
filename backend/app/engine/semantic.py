"""
Semantic Plagiarism Detection Engine
Uses sentence-transformers for embedding generation and
cosine similarity for paraphrase/semantic match detection.
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SemanticMatch:
    """A semantic similarity match result."""
    query_chunk_id: int
    source_chunk_id: int
    similarity: float
    match_type: str  # "high", "medium", "weak"
    query_text: str
    source_text: str
    source_id: str
    source_name: str


class SemanticEngine:
    """
    Sentence-transformer based semantic similarity engine.
    Detects paraphrased and semantically similar content.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        high_threshold: float = 0.88,
        med_threshold: float = 0.80,
        low_threshold: float = 0.70,
    ):
        self.model_name = model_name
        self.high_threshold = high_threshold
        self.med_threshold = med_threshold
        self.low_threshold = low_threshold
        self._model = None

    @property
    def model(self):
        """Lazy-load the sentence transformer model."""
        if self._model is None:
            logger.info(f"Loading model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        return self._model

    def encode(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        """Encode texts into embeddings."""
        if not texts:
            return np.array([])
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return np.array(embeddings, dtype=np.float32)

    def compute_similarity_matrix(
        self, query_embeddings: np.ndarray, source_embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute pairwise cosine similarity matrix."""
        if query_embeddings.size == 0 or source_embeddings.size == 0:
            return np.array([])
        # Since embeddings are normalized, dot product = cosine similarity
        return np.dot(query_embeddings, source_embeddings.T)

    def find_matches(
        self,
        query_chunks: list,
        source_chunks: list,
        source_id: str = "",
        source_name: str = "",
        query_embeddings: Optional[np.ndarray] = None,
        source_embeddings: Optional[np.ndarray] = None,
    ) -> list[SemanticMatch]:
        """Find semantic matches between query and source chunks."""
        if not query_chunks or not source_chunks:
            return []

        # Generate embeddings if not provided
        if query_embeddings is None:
            query_texts = [c.text for c in query_chunks]
            query_embeddings = self.encode(query_texts)

        if source_embeddings is None:
            source_texts = [c.text for c in source_chunks]
            source_embeddings = self.encode(source_texts)

        # Compute similarity matrix
        sim_matrix = self.compute_similarity_matrix(query_embeddings, source_embeddings)
        if sim_matrix.size == 0:
            return []

        matches = []

        for q_idx in range(len(query_chunks)):
            # Check length of the query chunk first
            query_chunk = query_chunks[q_idx]
            if len(query_chunk.text.split()) < 8:
                continue
                
            # Find best matching source chunk
            best_s_idx = int(np.argmax(sim_matrix[q_idx]))
            best_sim = float(sim_matrix[q_idx][best_s_idx])

            if best_sim < self.low_threshold:
                continue

            if best_sim >= self.high_threshold:
                match_type = "high"
            elif best_sim >= self.med_threshold:
                match_type = "medium"
            else:
                match_type = "weak"

            matches.append(SemanticMatch(
                query_chunk_id=query_chunks[q_idx].chunk_id,
                source_chunk_id=source_chunks[best_s_idx].chunk_id,
                similarity=best_sim,
                match_type=match_type,
                query_text=query_chunks[q_idx].text,
                source_text=source_chunks[best_s_idx].text,
                source_id=source_id,
                source_name=source_name,
            ))

        logger.info(
            f"Found {len(matches)} semantic matches against {source_name} "
            f"(high={sum(1 for m in matches if m.match_type == 'high')}, "
            f"med={sum(1 for m in matches if m.match_type == 'medium')}, "
            f"weak={sum(1 for m in matches if m.match_type == 'weak')})"
        )
        return matches

    def classify_match_type(self, similarity: float) -> str:
        """Classify similarity score into match type.
        
        Returns semantic match type labels (high/medium/weak), NOT 'exact'.
        Only true verbatim n-gram matches from ExactMatchEngine should be 'exact'.
        """
        if similarity >= self.high_threshold:
            return "high"
        elif similarity >= self.med_threshold:
            return "medium"
        elif similarity >= self.low_threshold:
            return "weak"
        return "none"

    def calculate_semantic_score(
        self, matches: list[SemanticMatch], total_chunks: int
    ) -> float:
        """Calculate percentage of chunks with semantic matches."""
        if total_chunks == 0:
            return 0.0
        matched = len(set(m.query_chunk_id for m in matches))
        return matched / total_chunks * 100
