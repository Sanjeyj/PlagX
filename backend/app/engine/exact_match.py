"""
Exact Plagiarism Detection Engine
Implements n-gram hashing and Rabin-Karp style matching
for detecting verbatim copied text.
"""

import logging
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Optional

from app.engine.config import ExactMatchConfig, default_config

logger = logging.getLogger(__name__)

PRIME = 101
BASE = 256


@dataclass
class ExactMatch:
    """An exact text match result."""
    query_start: int
    query_end: int
    source_start: int
    source_end: int
    matched_text: str
    ngram_size: int
    source_id: str
    source_name: str
    confidence: float = 1.0


class ExactMatchEngine:
    """
    N-gram hashing and Rabin-Karp style matching engine for
    detecting verbatim or near-verbatim copied text.
    """

    def __init__(
        self,
        ngram_size: Optional[int] = None,
        min_match_words: Optional[int] = None,
        config: Optional[ExactMatchConfig] = None
    ):
        self.config = config or default_config.exact_match
        self.ngram_size = ngram_size if ngram_size is not None else self.config.min_ngram
        self.min_match_words = min_match_words if min_match_words is not None else self.config.min_match_words

    def generate_ngrams(self, words: List[str], n: int = None) -> List[Tuple[str, int]]:
        """Generate n-grams with their starting word index."""
        n = n or self.ngram_size
        ngrams = []
        for i in range(len(words) - n + 1):
            gram = " ".join(words[i:i + n])
            ngrams.append((gram, i))
        return ngrams

    def hash_ngrams(self, words: List[str], n: int = None) -> dict[str, List[int]]:
        """Create a hash index of all n-grams for fast lookup."""
        n = n or self.ngram_size
        index = defaultdict(list)
        for gram, pos in self.generate_ngrams(words, n):
            h = hashlib.md5(gram.lower().encode()).hexdigest()
            index[h].append(pos)
        return index

    def find_matches(
        self,
        query_words: List[str],
        source_words: List[str],
        source_id: str = "",
        source_name: str = "",
    ) -> List[ExactMatch]:
        """
        Find exact n-gram matches between query and source documents.
        Uses hash-based matching with extension for longer matches.
        """
        if len(query_words) < self.ngram_size or len(source_words) < self.ngram_size:
            return []

        # Build hash index for source
        source_index = self.hash_ngrams(source_words)

        # Find matching n-grams in query
        query_ngrams = self.generate_ngrams(query_words)
        raw_matches = []

        for gram, q_pos in query_ngrams:
            h = hashlib.md5(gram.lower().encode()).hexdigest()
            if h in source_index:
                for s_pos in source_index[h]:
                    # Verify actual match (not just hash collision)
                    q_gram = " ".join(query_words[q_pos:q_pos + self.ngram_size]).lower()
                    s_gram = " ".join(source_words[s_pos:s_pos + self.ngram_size]).lower()
                    if q_gram == s_gram:
                        raw_matches.append((q_pos, s_pos))

        if not raw_matches:
            return []

        # Extend and merge matches into longest contiguous sequences
        matches = self._extend_matches(
            raw_matches, query_words, source_words, source_id, source_name
        )

        # Filter by minimum length and common academic phrases
        if self.config.whitelist_filter:
            from app.engine.citation_excluder import WHITELIST_PHRASES
            whitelist_set = set(p.lower().strip() for p in WHITELIST_PHRASES)
        else:
            whitelist_set = set()

        filtered_matches = []
        for m in matches:
            if m.ngram_size < self.min_match_words:
                continue
            text_lower = m.matched_text.lower().strip()
            if text_lower in whitelist_set:
                continue
            filtered_matches.append(m)

        logger.info(f"Found {len(filtered_matches)} exact matches against {source_name}")
        return filtered_matches

    def _extend_matches(
        self,
        raw_matches: List[Tuple[int, int]],
        query_words: List[str],
        source_words: List[str],
        source_id: str,
        source_name: str,
    ) -> List[ExactMatch]:
        """
        Extend n-gram matches into longest possible contiguous sequences.
        Recovers longest valid exact regions without prematurely burning candidate tokens.
        """
        if not raw_matches:
            return []

        raw_matches.sort()
        candidate_spans = []

        # Forward extension for each seed hit
        for q_start, s_start in raw_matches:
            q_end = q_start + self.ngram_size
            s_end = s_start + self.ngram_size

            # Extend forward as far as identical
            while (
                q_end < len(query_words)
                and s_end < len(source_words)
                and query_words[q_end].lower() == source_words[s_end].lower()
            ):
                q_end += 1
                s_end += 1

            match_len = q_end - q_start
            matched_text = " ".join(query_words[q_start:q_end])

            candidate_spans.append(ExactMatch(
                query_start=q_start,
                query_end=q_end,
                source_start=s_start,
                source_end=s_end,
                matched_text=matched_text,
                ngram_size=match_len,
                source_id=source_id,
                source_name=source_name,
                confidence=1.0,
            ))

        # Merge overlapping/adjacent candidates while dynamically updating full matched text
        return self._merge_adjacent(candidate_spans, query_words)

    def _merge_adjacent(
        self,
        matches: List[ExactMatch],
        query_words: List[str]
    ) -> List[ExactMatch]:
        """
        Merge adjacent or overlapping exact matches.
        Guarantees matched_text, ngram_size, offsets, and token counts
        represent the complete merged region.
        """
        if not matches:
            return []

        matches.sort(key=lambda m: (m.query_start, -m.ngram_size))
        merged: List[ExactMatch] = []

        merge_gap = getattr(self.config, 'merge_gap', 1)

        for current in matches:
            if not merged:
                merged.append(current)
                continue

            last = merged[-1]
            # Check if current overlaps or is adjacent within merge_gap
            if current.query_start <= last.query_end + merge_gap:
                new_q_start = last.query_start
                new_q_end = max(last.query_end, current.query_end)
                new_s_start = last.source_start
                new_s_end = max(last.source_end, current.source_end)
                new_match_len = new_q_end - new_q_start

                # Reconstruct full matched_text from query_words across the complete merged span
                full_matched_text = " ".join(query_words[new_q_start:new_q_end])

                merged[-1] = ExactMatch(
                    query_start=new_q_start,
                    query_end=new_q_end,
                    source_start=new_s_start,
                    source_end=new_s_end,
                    matched_text=full_matched_text,
                    ngram_size=new_match_len,
                    source_id=last.source_id,
                    source_name=last.source_name,
                    confidence=max(last.confidence, current.confidence),
                )
            else:
                merged.append(current)

        return merged

    def calculate_exact_score(self, matches: List[ExactMatch], total_words: int) -> float:
        """Calculate the unique percentage of text that is exactly matched."""
        if total_words == 0:
            return 0.0
        matched_words = set()
        for m in matches:
            for i in range(m.query_start, m.query_end):
                matched_words.add(i)
        return len(matched_words) / total_words * 100
