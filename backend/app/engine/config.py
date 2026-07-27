"""
Global Configuration for PlagX Enterprise Similarity Engine v2
All thresholds, weights, and parameters are configurable. No hardcoded magic numbers.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class ExactMatchConfig:
    min_ngram: int = 5
    min_match_words: int = 5
    merge_gap: int = 1
    max_gap: int = 3
    whitelist_filter: bool = True


@dataclass
class SemanticConfig:
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    top_k: int = 3
    high_threshold: float = 0.85
    med_threshold: float = 0.75
    low_threshold: float = 0.65
    min_words: int = 6
    suppress_common_phrases: bool = True


@dataclass
class DocumentStructureConfig:
    bibliography_detection: bool = True
    metadata_detection: bool = True
    header_footer_detection: bool = True
    code_block_detection: bool = True


@dataclass
class ExclusionConfig:
    exclude_bibliography: bool = True
    exclude_quotes: bool = False
    exclude_small_matches: bool = True
    small_match_word_limit: int = 5


@dataclass
class CitationConfig:
    quoted_weight: float = 0.05
    properly_cited_weight: float = 0.10
    missing_quotation_weight: float = 0.80
    missing_citation_weight: float = 0.60
    uncited_copy_weight: float = 1.00


@dataclass
class RarityConfig:
    enabled: bool = True
    min_idf: float = 1.0
    common_phrase_penalty: float = 0.2
    rare_phrase_boost: float = 1.2


@dataclass
class ConfidenceConfig:
    exact_weight: float = 1.0
    high_semantic_weight: float = 0.85
    med_semantic_weight: float = 0.65
    low_semantic_weight: float = 0.35


@dataclass
class SourceAttributionConfig:
    collapse_mirrors: bool = True
    dominant_source_preference: str = "max_coverage"


@dataclass
class ScoringConfig:
    confidence_weights: Dict[str, float] = field(default_factory=lambda: {
        "exact": 1.0,
        "high_semantic": 0.85,
        "med_semantic": 0.65,
        "low_semantic": 0.35
    })
    density_weight: float = 0.10
    engine_version: str = "2.0.0"
    scoring_version: str = "2.0.0"


@dataclass
class HighlightConfig:
    merge_distance: int = 10
    trim_whitespace: bool = True
    align_sentence_boundaries: bool = True


@dataclass
class SimilarityConfig:
    exact_match: ExactMatchConfig = field(default_factory=ExactMatchConfig)
    semantic: SemanticConfig = field(default_factory=SemanticConfig)
    structure: DocumentStructureConfig = field(default_factory=DocumentStructureConfig)
    exclusion: ExclusionConfig = field(default_factory=ExclusionConfig)
    citation: CitationConfig = field(default_factory=CitationConfig)
    rarity: RarityConfig = field(default_factory=RarityConfig)
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)
    source_attribution: SourceAttributionConfig = field(default_factory=SourceAttributionConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    highlight: HighlightConfig = field(default_factory=HighlightConfig)
    engine_version: str = "2.0.0"


# Default global instance
default_config = SimilarityConfig()
