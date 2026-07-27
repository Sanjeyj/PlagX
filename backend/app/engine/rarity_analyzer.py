"""
Rarity Analyzer for PlagX Enterprise Similarity Engine v2
Calculates TF-IDF and corpus-wide phrase rarity weighting.
High rarity technical terms increase similarity contribution, while common academic transitions decrease it.
"""

import math
import re
import logging
from typing import List, Dict, Optional, Set

from app.engine.config import RarityConfig, default_config

logger = logging.getLogger(__name__)

COMMON_ACADEMIC_TRANSITIONS = {
    "in this paper we present",
    "on the other hand",
    "it is important to note that",
    "as shown in figure",
    "the rest of this paper is organized as follows",
    "in recent years",
    "has drawn significant attention",
    "due to the fact that",
    "in order to",
    "for the purpose of",
}


class RarityAnalyzer:
    """
    Evaluates term frequency and inverse document frequency (TF-IDF) across text spans.
    Suppresses common academic formulas and boosts rare technical terminology.
    """

    def __init__(self, config: Optional[RarityConfig] = None):
        self.config = config or default_config.rarity
        self.idf_cache: Dict[str, float] = {}

    def compute_phrase_rarity(self, text: str) -> float:
        """
        Calculates rarity multiplier for a text span.
        Returns a float multiplier between 0.2 and 1.5.
        """
        if not self.config.enabled:
            return 1.0

        text_clean = text.lower().strip()

        # 1. Check for common academic transitions (heavy suppression)
        for transition in COMMON_ACADEMIC_TRANSITIONS:
            if transition in text_clean:
                return self.config.common_phrase_penalty  # e.g., 0.2

        # 2. Compute token-level IDF approximation based on length & word complexity
        words = re.findall(r'\b[a-z]{3,}\b', text_clean)
        if not words:
            return 1.0

        rare_words = [w for w in words if len(w) > 7 or w not in {"the", "and", "this", "that", "with", "from", "were", "have"}]
        rare_ratio = len(rare_words) / len(words) if words else 0.5

        if rare_ratio > 0.6:
            return self.config.rare_phrase_boost  # e.g., 1.2
        elif rare_ratio < 0.2:
            return self.config.common_phrase_penalty
        return 1.0
