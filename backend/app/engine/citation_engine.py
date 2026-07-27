"""
Citation Engine for PlagX Enterprise Similarity Engine v2
Detects quoted text, inline citations, citation proximity, and reference mappings.
Assigns structured citation_status and configurable weight modifiers.
"""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

from app.engine.config import CitationConfig, default_config

logger = logging.getLogger(__name__)


@dataclass
class CitationAnalysisResult:
    citation_status: str  # Properly Quoted, Properly Cited, Missing Quotation, Missing Citation, Uncited Copy
    weight_modifier: float
    is_quoted: bool
    is_cited: bool


class CitationEngine:
    """
    Analyzes quote marks, parenthetical/numbered inline citations, proximity to references,
    and assigns structured citation_status with configurable weight modifiers.
    """

    CITATION_PATTERNS = [
        r'\[\d+(?:--?\d+)?\]',  # [1], [1-3]
        r'\((?:[A-Z][a-zA-Z\s]+(?:et\s+al\.)?,\s*\d{4}[a-z]?)\)',  # (Smith et al., 2024)
        r'\b(?:[A-Z][a-zA-Z]+ et al\.,?\s*\(\d{4}\))\b',  # Smith et al. (2024)
    ]

    QUOTE_PATTERNS = [
        r'"[^"]+"',
        r'“[^”]+”',
        r'«[^»]+»',
    ]

    def __init__(self, config: Optional[CitationConfig] = None):
        self.config = config or default_config.citation

    def analyze_span(self, full_text: str, start_char: int, end_char: int, is_exact: bool) -> CitationAnalysisResult:
        """Classify citation status for a match span in full_text."""
        span_text = full_text[start_char:end_char]

        # Check if span is inside quotes or contains quotes
        is_quoted = self._check_quoted(full_text, start_char, end_char)

        # Check if inline citation is nearby (within 120 chars)
        is_cited = self._check_cited_proximity(full_text, start_char, end_char)

        if is_quoted and is_cited:
            status = "Properly Quoted"
            weight = self.config.quoted_weight
        elif is_cited and not is_quoted:
            status = "Properly Cited"
            weight = self.config.properly_cited_weight
        elif is_quoted and not is_cited:
            status = "Missing Citation"
            weight = self.config.missing_citation_weight
        elif is_exact and not is_quoted and not is_cited:
            status = "Uncited Copy"
            weight = self.config.uncited_copy_weight
        else:
            status = "Missing Quotation" if is_exact else "Uncited Copy"
            weight = self.config.missing_quotation_weight if is_exact else self.config.uncited_copy_weight

        return CitationAnalysisResult(
            citation_status=status,
            weight_modifier=weight,
            is_quoted=is_quoted,
            is_cited=is_cited
        )

    def _check_quoted(self, full_text: str, start_char: int, end_char: int) -> bool:
        """Check if span is enclosed within quote marks."""
        prefix = full_text[max(0, start_char - 5):start_char]
        suffix = full_text[end_char:min(len(full_text), end_char + 5)]

        if ('"' in prefix and '"' in suffix) or ('“' in prefix and '”' in suffix):
            return True

        span_text = full_text[start_char:end_char]
        for pattern in self.QUOTE_PATTERNS:
            if re.search(pattern, span_text):
                return True
        return False

    def _check_cited_proximity(self, full_text: str, start_char: int, end_char: int) -> bool:
        """Check if an inline citation exists within 120 characters of the match span."""
        window_start = max(0, start_char - 120)
        window_end = min(len(full_text), end_char + 120)
        window_text = full_text[window_start:window_end]

        for pattern in self.CITATION_PATTERNS:
            if re.search(pattern, window_text):
                return True
        return False
