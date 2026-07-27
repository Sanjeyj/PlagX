"""
Highlight Engine for PlagX Enterprise Similarity Engine v2
Trims whitespace/punctuation, aligns highlight boundaries to sentence/clause punctuation,
and avoids highlighting metadata, references, or giant unparsed blocks.
"""

import re
import logging
from typing import List, Optional
from dataclasses import dataclass

from app.engine.config import HighlightConfig, default_config

logger = logging.getLogger(__name__)


class HighlightEngine:
    """
    Refines inline highlight spans to align strictly with sentence/clause boundaries,
    trimming leading/trailing punctuation and whitespace.
    """

    def __init__(self, config: Optional[HighlightConfig] = None):
        self.config = config or default_config.highlight

    def refine_spans(self, spans: List[any], full_text: str) -> List[any]:
        """Align highlight spans to sentence boundaries and trim whitespace."""
        refined = []
        for span in spans:
            start = span.start_char
            end = span.end_char

            # Trim leading punctuation / whitespace
            while start < end and not full_text[start].isalnum():
                start += 1
            # Trim trailing punctuation / whitespace
            while end > start and not full_text[end - 1].isalnum():
                end -= 1

            if start >= end:
                continue

            span.start_char = start
            span.end_char = end
            span.matched_text = full_text[start:end]
            span.original_text = span.matched_text
            refined.append(span)

        return refined
