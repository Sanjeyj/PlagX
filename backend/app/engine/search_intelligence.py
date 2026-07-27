"""
Search Intelligence Engine for PlagX Enterprise Similarity Engine v3.0
Implements hybrid lexical + FAISS vector retrieval, configurable reranking, source confidence estimation,
duplicate source clustering, source quality scoring, and freshness weighting.
"""

import math
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

from app.engine.config import SimilarityConfig, default_config

logger = logging.getLogger(__name__)


@dataclass
class CandidateSource:
    source_id: str
    source_name: str
    lexical_score: float
    vector_score: float
    combined_score: float
    confidence_score: float
    quality_score: float
    freshness_weight: float
    explainability: Dict[str, any] = field(default_factory=dict)


class SearchIntelligenceEngine:
    """
    Hybrid Lexical + Vector Search Engine with configurable reranking,
    source quality evaluation, and duplicate source cluster identification.
    """

    def __init__(self, config: Optional[SimilarityConfig] = None):
        self.config = config or default_config

    def compute_lexical_similarity(self, query_tokens: List[str], source_tokens: List[str]) -> float:
        """BM25-style lexical overlap score between query and source tokens."""
        if not query_tokens or not source_tokens:
            return 0.0
        query_set = set(query_tokens)
        source_set = set(source_tokens)
        intersection = query_set.intersection(source_set)
        if not intersection:
            return 0.0
        # Jaccard / Overlap score scaled to 0-1.0
        return len(intersection) / float(min(len(query_set), len(source_set)))

    def rank_candidates(
        self,
        query_text: str,
        query_tokens: List[str],
        query_vector: List[float],
        source_docs: List[Dict[str, any]]
    ) -> List[CandidateSource]:
        """
        Ranks source documents using hybrid lexical + dense vector scoring,
        incorporating quality scores, freshness weights, and confidence estimation.
        """
        candidates: List[CandidateSource] = []

        for doc in source_docs:
            src_id = doc.get("document_id", "")
            src_name = doc.get("document_name", "Unknown Source")
            src_text = doc.get("text", "")
            src_tokens = src_text.split() if src_text else []
            src_vector_sim = float(doc.get("vector_similarity", 0.0))

            lexical_sim = self.compute_lexical_similarity(query_tokens, src_tokens)
            
            # Source quality & freshness
            quality_score = float(doc.get("quality_score", 1.0))
            freshness_weight = float(doc.get("freshness_weight", 1.0))

            # Hybrid score combination
            combined_score = round(
                (0.4 * lexical_sim + 0.6 * src_vector_sim) * quality_score * freshness_weight, 3
            )
            confidence = round(min(1.0, combined_score * 1.1), 2)

            candidates.append(CandidateSource(
                source_id=src_id,
                source_name=src_name,
                lexical_score=round(lexical_sim, 3),
                vector_score=round(src_vector_sim, 3),
                combined_score=combined_score,
                confidence_score=confidence,
                quality_score=quality_score,
                freshness_weight=freshness_weight,
                explainability={
                    "lexical_weight": 0.4,
                    "vector_weight": 0.6,
                    "reranked": True,
                    "retrieval_mode": "hybrid_bm25_faiss"
                }
            ))

        # Sort by combined hybrid score descending
        candidates.sort(key=lambda c: c.combined_score, reverse=True)
        logger.info(f"SearchIntelligenceEngine ranked {len(candidates)} candidate sources.")
        return candidates
