"""
Turnitin-Style Scoring Engine
Calculates plagiarism score based on word coverage and source statistics.
"""

import logging
from dataclasses import dataclass

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


class AdaptiveThresholds:
    """Dynamic thresholds based on document characteristics (kept for backward compatibility)."""

    PROFILES = {
        "technical": {"semantic": 0.82, "exact_min_words": 8, "density_weight": 0.15},
        "general": {"semantic": 0.75, "exact_min_words": 6, "density_weight": 0.20},
        "code": {"semantic": 0.90, "exact_min_words": 10, "density_weight": 0.10},
        "default": {"semantic": 0.75, "exact_min_words": 6, "density_weight": 0.20},
    }

    @classmethod
    def detect_document_type(cls, text: str) -> str:
        """Detect document type based on content analysis."""
        text_lower = text.lower()
        word_count = len(text_lower.split())

        # Code detection
        code_indicators = [
            "def ", "class ", "import ", "function ", "var ", "const ",
            "return ", "if (", "for (", "while (", "=>", "->",
        ]
        code_score = sum(1 for ind in code_indicators if ind in text_lower)
        if code_score > 3:
            return "code"

        # Technical paper detection
        tech_indicators = [
            "abstract", "methodology", "hypothesis", "algorithm",
            "equation", "theorem", "dataset", "experiment",
            "statistical", "coefficient", "regression", "neural network",
        ]
        tech_score = sum(1 for ind in tech_indicators if ind in text_lower)
        if tech_score > 3:
            return "technical"

        return "general"

    @classmethod
    def get_thresholds(cls, document_type: str) -> dict:
        return cls.PROFILES.get(document_type, cls.PROFILES["default"])


class HybridScorer:
    """
    Calculates Turnitin-style plagiarism score: matched_words / total_words * 100.
    Keeps exact and semantic scores as breakdown metrics only.
    """

    def __init__(
        self,
        exact_weight: float = 0.40,
        semantic_weight: float = 0.40,
        density_weight: float = 0.20,
    ):
        # Kept for backward compatibility but unused for Turnitin scoring
        self.exact_weight = exact_weight
        self.semantic_weight = semantic_weight
        self.density_weight = density_weight

    def normalize_score(self, raw_sim: float) -> float:
        """Piecewise nonlinear score normalization to match Turnitin behavior.
        
        Mapping (approximate):
          5% raw  →  3.5%    | 30% raw  → 18%
          45% raw → 31%      | 60% raw  → 45%
          75% raw → 63%      | 90% raw  → 82%
          100% raw → 100%
        """
        x = min(max(raw_sim, 0.0), 100.0)
        if x <= 10.0:
            # Light suppression for very low matches
            y = x * 0.7
        elif x <= 30.0:
            # Gentle curve through low range
            y = 7.0 + 11.0 * ((x - 10.0) / 20.0) ** 1.2
        elif x <= 60.0:
            # Moderate mid-range  
            y = 18.0 + 27.0 * ((x - 30.0) / 30.0) ** 1.1
        elif x <= 85.0:
            # High range flattens slightly
            y = 45.0 + 30.0 * ((x - 60.0) / 25.0) ** 0.9
        else:
            # Linear to 100%
            y = 75.0 + 25.0 * ((x - 85.0) / 15.0)
        return round(min(max(y, 0.0), 100.0), 1)

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
        """Calculate the final Turnitin-style plagiarism score.
        
        If raw_weighted_sim is provided, it is used directly as the raw
        percentage for normalization (preferred path from pipeline).
        Otherwise falls back to matched_words / total_words.
        """
        if total_words <= 0:
            overall = 0.0
        elif raw_weighted_sim is not None:
            overall = self.normalize_score(raw_weighted_sim)
        else:
            raw_sim = (matched_words / total_words) * 100.0
            overall = self.normalize_score(raw_sim)
            
        overall = min(overall, 100.0)
        overall = round(overall, 1)

        # Cap individual breakdown scores at 100
        exact_score = min(exact_score, 100.0)
        semantic_score = min(semantic_score, 100.0)
        source_density = min(source_density, 100.0)

        risk_level = self.classify_risk(overall)

        result = ScoringResult(
            overall_score=overall,
            exact_score=round(exact_score, 1),
            semantic_score=round(semantic_score, 1),
            source_density_score=round(source_density, 1),
            risk_level=risk_level,
            matched_word_count=matched_words,
            total_word_count=total_words,
            source_count=source_count,
            exact_match_count=exact_match_count,
            semantic_match_count=semantic_match_count,
        )

        logger.info(
            f"Turnitin Score: {overall}% ({risk_level}) | "
            f"Exact (Breakdown): {exact_score:.1f}% | Semantic (Breakdown): {semantic_score:.1f}% | "
            f"Density: {source_density:.1f}% | Sources: {source_count}"
        )
        return result

    def classify_risk(self, score: float) -> str:
        """Classify overall score into Turnitin risk bands."""
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

    def calculate_source_density(
        self,
        source_count: int,
        total_words: int,
    ) -> float:
        """Calculate source density as source diversity per 100 words."""
        if total_words == 0:
            return 0.0
        return (source_count / (total_words / 100.0))

    def calculate_paragraph_scores(
        self,
        paragraphs: list,
        matched_spans: list,
    ) -> list[dict]:
        """Calculate per-paragraph plagiarism scores."""
        para_scores = []

        for para in paragraphs:
            para_chars = para.end_char - para.start_char
            if para_chars == 0:
                para_scores.append({
                    "paragraph_index": para.paragraph_index,
                    "score": 0.0,
                    "match_type": None,
                    "source_indices": [],
                })
                continue

            # Find spans that overlap with this paragraph
            overlap_chars = 0
            sources = set()
            best_type = None
            type_priority = {"exact": 3, "semantic": 2, "weak": 1}

            for span in matched_spans:
                if span.start_char < para.end_char and span.end_char > para.start_char:
                    overlap_start = max(span.start_char, para.start_char)
                    overlap_end = min(span.end_char, para.end_char)
                    overlap_chars += overlap_end - overlap_start
                    if hasattr(span, 'source_index') and span.source_index is not None:
                        sources.add(span.source_index)

                    if best_type is None or type_priority.get(span.match_type, 0) > type_priority.get(best_type, 0):
                        best_type = span.match_type

            score = min((overlap_chars / para_chars) * 100, 100.0)

            para_scores.append({
                "paragraph_index": para.paragraph_index,
                "score": round(score, 1),
                "match_type": best_type,
                "source_indices": list(sources),
            })

        return para_scores
