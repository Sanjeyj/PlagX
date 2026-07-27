"""
Turnitin-Style Academic Similarity Scoring Engine v2
Implements Weighted Academic Similarity Model:
Similarity = Unique Suspicious Coverage x Confidence x Context x Rarity x Citation Adjustment
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Dict

from app.engine.config import ScoringConfig, default_config

logger = logging.getLogger(__name__)


@dataclass
class ScoringResult:
    """Complete scoring result."""
    overall_score: float
    exact_score: float
    semantic_score: float
    source_density_score: float
    risk_level: str
    matched_word_count: int
    total_word_count: int
    source_count: int
    exact_match_count: int
    semantic_match_count: int
    engine_version: str = "2.0.0"
    scoring_version: str = "2.0.0"


class AdaptiveThresholds:
    """Dynamic profiles based on document type."""
    PROFILES = {
        "technical": {"semantic": 0.82, "exact_min_words": 5},
        "general": {"semantic": 0.75, "exact_min_words": 5},
        "code": {"semantic": 0.90, "exact_min_words": 8},
        "default": {"semantic": 0.75, "exact_min_words": 5},
    }

    @classmethod
    def detect_document_type(cls, text: str) -> str:
        text_lower = text.lower()
        if sum(1 for ind in ["def ", "class ", "import ", "function ", "var "] if ind in text_lower) > 3:
            return "code"
        if sum(1 for ind in ["abstract", "methodology", "hypothesis", "algorithm"] if ind in text_lower) > 3:
            return "technical"
        return "general"


class HybridScorer:
    """
    Weighted Academic Similarity Scoring Engine v2.
    Calculates overall score based on unique suspicious token coverage multiplied by confidence, rarity, and citation adjustments.
    """

    def __init__(self, config: Optional[ScoringConfig] = None, **kwargs):
        self.config = config or default_config.scoring

    def calculate_score(
        self,
        exact_score: float,
        semantic_score: float,
        source_density: float,
        total_words: int,
        matched_words: int,
        source_count: int,
        exact_match_count: int,
        semantic_match_count: int,
        document_type: str = "general",
        raw_weighted_sim: float = None,
    ) -> ScoringResult:
        """
        Calculates the Weighted Academic Similarity score.
        """
        if total_words <= 0:
            overall = 0.0
        elif raw_weighted_sim is not None:
            overall = round(min(100.0, max(0.0, raw_weighted_sim)), 1)
        else:
            raw_sim = (matched_words / total_words) * 100.0
            overall = round(min(100.0, max(0.0, raw_sim)), 1)

        risk_level = self.classify_risk(overall)

        return ScoringResult(
            overall_score=overall,
            exact_score=round(min(100.0, exact_score), 1),
            semantic_score=round(min(100.0, semantic_score), 1),
            source_density_score=round(min(100.0, source_density), 1),
            risk_level=risk_level,
            matched_word_count=matched_words,
            total_word_count=total_words,
            source_count=source_count,
            exact_match_count=exact_match_count,
            semantic_match_count=semantic_match_count,
            engine_version=self.config.engine_version,
            scoring_version=self.config.scoring_version,
        )

    def classify_risk(self, score: float) -> str:
        """Classify overall score into risk bands."""
        if score == 0:
            return "none"
        elif score <= 24:
            return "low"
        elif score <= 49:
            return "moderate"
        elif score <= 74:
            return "significant"
        else:
            return "high"

    def calculate_source_density(self, source_count: int, total_words: int) -> float:
        if total_words == 0:
            return 0.0
        return (source_count / (total_words / 100.0))

    def calculate_paragraph_scores(self, paragraphs: list, matched_spans: list) -> list[dict]:
        para_scores = []
        for p in paragraphs:
            p_len = len(p.text.split()) or 1
            p_matched = 0
            for s in matched_spans:
                if s.start_char < p.end_char and s.end_char > p.start_char:
                    overlap_chars = max(0, min(s.end_char, p.end_char) - max(s.start_char, p.start_char))
                    p_matched += max(1, overlap_chars // 5)
            pct = round(min(100.0, (p_matched / p_len) * 100.0), 1)
            para_scores.append({
                "paragraph_index": p.paragraph_index,
                "score": pct,
                "text": p.text[:50] + "..."
            })
        return para_scores
