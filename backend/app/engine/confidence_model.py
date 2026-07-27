"""
Confidence Model for PlagX Enterprise Similarity Engine v2
Computes multi-factor confidence scores for every detected match span.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from app.engine.config import ConfidenceConfig, default_config

logger = logging.getLogger(__name__)


class ConfidenceModel:
    """
    Computes span confidence scores based on exactness, semantic certainty,
    continuity, rarity, source agreement, document section context, and citation status.
    """

    def __init__(self, config: Optional[ConfidenceConfig] = None):
        self.config = config or default_config.confidence

    def compute_confidence(
        self,
        match_type: str,
        similarity: float,
        word_count: int,
        rarity_score: float,
        citation_weight: float,
        section_policy: str = "primary"
    ) -> float:
        """
        Calculates a confidence score between 0.0 and 1.0.
        """
        # 1. Base score from match type / similarity
        if match_type == "exact":
            base = self.config.exact_weight
        elif similarity >= 0.85:
            base = self.config.high_semantic_weight
        elif similarity >= 0.75:
            base = self.config.med_semantic_weight
        else:
            base = self.config.low_semantic_weight

        # 2. Continuity factor (longer spans increase confidence)
        if word_count >= 20:
            continuity = 1.0
        elif word_count >= 10:
            continuity = 0.85
        elif word_count >= 5:
            continuity = 0.70
        else:
            continuity = 0.50

        # 3. Context & section policy factor
        context_factor = 1.0 if section_policy == "primary" else (0.3 if section_policy == "suppress" else 0.0)

        # Final composite confidence calculation
        confidence = base * continuity * context_factor * min(1.2, max(0.5, rarity_score))
        return round(min(1.0, max(0.0, confidence)), 2)
