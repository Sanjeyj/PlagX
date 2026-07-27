"""
Source Attribution Engine for PlagX Enterprise Similarity Engine v2
Manages region-level ownership, dominant source selection, collapsing mirrored internet/repository sources,
and unique non-overlapping source contribution calculation.
"""

import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field

from app.engine.config import SourceAttributionConfig, default_config

logger = logging.getLogger(__name__)


@dataclass
class SourceAttributionResult:
    dominant_source_id: str
    dominant_source_name: str
    unique_matched_words: int
    unique_percentage: float
    color: str = ""


class SourceAttributionEngine:
    """
    Selects dominant source for overlapping match regions, collapses mirrored sources,
    and computes unique non-overlapping source contributions.
    """

    def __init__(self, config: Optional[SourceAttributionConfig] = None):
        self.config = config or default_config.source_attribution

    def compute_unique_attributions(
        self,
        finalized_spans: List[any],
        total_tokens: int,
        source_names_map: Dict[str, str]
    ) -> List[SourceAttributionResult]:
        """
        Computes non-overlapping unique source percentage contributions.
        """
        if total_tokens <= 0:
            return []

        source_words: Dict[str, Set[int]] = {}

        for span in finalized_spans:
            src_id = span.top_source_id
            if src_id not in source_words:
                source_words[src_id] = set()

            # Attribute tokens to top source
            start_word = getattr(span, 'start_word', span.start_char // 5)
            end_word = getattr(span, 'end_word', span.end_char // 5)
            for w_idx in range(start_word, max(start_word + 1, end_word)):
                source_words[src_id].add(w_idx)

        # Deduplicate overlap across sources (assign each token to first/dominant source)
        claimed_tokens: Set[int] = set()
        results: List[SourceAttributionResult] = []

        # Sort sources by total matched words descending
        sorted_sources = sorted(source_words.keys(), key=lambda k: len(source_words[k]), reverse=True)

        for src_id in sorted_sources:
            unique_tokens = source_words[src_id] - claimed_tokens
            claimed_tokens.update(unique_tokens)

            word_count = len(unique_tokens)
            pct = round((word_count / total_tokens) * 100.0, 1)

            if word_count > 0 or pct > 0.0:
                results.append(SourceAttributionResult(
                    dominant_source_id=src_id,
                    dominant_source_name=source_names_map.get(src_id, "Unknown Source"),
                    unique_matched_words=word_count,
                    unique_percentage=pct,
                ))

        return results
