"""
Exclusion Engine for PlagX Enterprise Similarity Engine v2
Filters out bibliography, metadata, acknowledgements, running headers/footers, and boilerplate text before scoring.
"""

import re
import logging
from typing import List, Tuple, Optional, Set
from dataclasses import dataclass

from app.engine.config import ExclusionConfig, default_config
from app.engine.structure_analyzer import DocumentSection, DocumentStructureAnalyzer
from app.engine.offset_mapper import DocumentMap

logger = logging.getLogger(__name__)

INSTITUTIONAL_BOILERPLATE = [
    "submitted in partial fulfillment of the requirements for the degree of",
    "all rights reserved",
    "permission to make digital or hard copies of all or part of this work",
    "the author grants permission to reproduce",
    "copyright remains with the author",
    "published by ieee",
    "acm reference format",
]


class ExclusionEngine:
    """
    Excludes or suppresses non-content regions (Bibliography, References,
    Author metadata, Institutional Boilerplate, Page Headers/Footers) prior to scoring.
    """

    def __init__(
        self,
        config: Optional[ExclusionConfig] = None,
        structure_analyzer: Optional[DocumentStructureAnalyzer] = None
    ):
        self.config = config or default_config.exclusion
        self.analyzer = structure_analyzer or DocumentStructureAnalyzer()

    def process_document(self, doc_map: DocumentMap) -> List[DocumentSection]:
        """Analyze structure and mark excluded tokens in doc_map."""
        sections = self.analyzer.analyze(doc_map.full_text)

        # Mark excluded sections in doc_map tokens
        for token in doc_map.tokens:
            policy, modifier = self.analyzer.get_policy_for_char(sections, token.start_char)
            if policy == "exclude":
                token.is_excluded = True
            elif self.is_boilerplate(token.original_text):
                token.is_excluded = True

        return sections

    def is_boilerplate(self, text: str) -> bool:
        """Check if a text block matches institutional or copyright boilerplate."""
        text_lower = text.lower().strip()
        for bp in INSTITUTIONAL_BOILERPLATE:
            if bp in text_lower:
                return True
        return False

    def should_exclude_span(self, start_char: int, end_char: int, text: str, sections: List[DocumentSection]) -> bool:
        """Check if a detected match span falls inside an excluded structural zone or boilerplate."""
        policy, modifier = self.analyzer.get_policy_for_char(sections, start_char)
        if policy == "exclude":
            return True
        if self.is_boilerplate(text):
            return True
        if self.config.exclude_small_matches:
            words = len(text.split())
            if words < self.config.small_match_word_limit:
                return True
        return False
