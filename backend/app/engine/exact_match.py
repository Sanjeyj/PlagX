"""
Exact Plagiarism Detection Engine
Implements n-gram hashing and Rabin-Karp style matching
for detecting verbatim copied text.
"""

import logging
import hashlib
from collections import defaultdict
from dataclasses import dataclass

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

    def __init__(self, ngram_size: int = 5, min_match_words: int = 8):
        self.ngram_size = ngram_size
        self.min_match_words = min_match_words

    def generate_ngrams(self, words: list[str], n: int = None) -> list[tuple[str, int]]:
        """Generate n-grams with their starting word index."""
        n = n or self.ngram_size
        ngrams = []
        for i in range(len(words) - n + 1):
            gram = " ".join(words[i:i + n])
            ngrams.append((gram, i))
        return ngrams

    def hash_ngrams(self, words: list[str], n: int = None) -> dict[str, list[int]]:
        """Create a hash index of all n-grams for fast lookup."""
        n = n or self.ngram_size
        index = defaultdict(list)
        for gram, pos in self.generate_ngrams(words, n):
            h = hashlib.md5(gram.lower().encode()).hexdigest()
            index[h].append(pos)
        return index

    def find_matches(
        self,
        query_words: list[str],
        source_words: list[str],
        source_id: str = "",
        source_name: str = "",
    ) -> list[ExactMatch]:
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
        from app.engine.citation_excluder import WHITELIST_PHRASES
        whitelist_set = set(p.lower().strip() for p in WHITELIST_PHRASES)
        
        filtered_matches = []
        for m in matches:
            if m.ngram_size < self.min_match_words:
                continue
            text_lower = m.matched_text.lower().strip()
            if text_lower in whitelist_set:
                continue
            filtered_matches.append(m)
        matches = filtered_matches

        logger.info(f"Found {len(matches)} exact matches against {source_name}")
        return matches

    def _extend_matches(
        self,
        raw_matches: list[tuple[int, int]],
        query_words: list[str],
        source_words: list[str],
        source_id: str,
        source_name: str,
    ) -> list[ExactMatch]:
        """Extend n-gram matches into longest possible contiguous sequences."""
        if not raw_matches:
            return []

        # Sort by query position
        raw_matches.sort()
        extended = []
        used = set()

        for q_start, s_start in raw_matches:
            if q_start in used:
                continue

            # Extend match forward
            q_end = q_start + self.ngram_size
            s_end = s_start + self.ngram_size

            while (
                q_end < len(query_words)
                and s_end < len(source_words)
                and query_words[q_end].lower() == source_words[s_end].lower()
            ):
                q_end += 1
                s_end += 1

            match_len = q_end - q_start
            matched_text = " ".join(query_words[q_start:q_end])

            # Mark positions as used
            for pos in range(q_start, q_end):
                used.add(pos)

            extended.append(ExactMatch(
                query_start=q_start,
                query_end=q_end,
                source_start=s_start,
                source_end=s_end,
                matched_text=matched_text,
                ngram_size=match_len,
                source_id=source_id,
                source_name=source_name,
                confidence=min(1.0, match_len / 10),
            ))

        return self._merge_adjacent(extended)

    def _merge_adjacent(self, matches: list[ExactMatch]) -> list[ExactMatch]:
        """Merge adjacent or overlapping exact matches."""
        if not matches:
            return []

        matches.sort(key=lambda m: m.query_start)
        merged = [matches[0]]

        for current in matches[1:]:
            last = merged[-1]
            # If overlapping or adjacent (within 1 word gap)
            if current.query_start <= last.query_end + 1:
                merged[-1] = ExactMatch(
                    query_start=last.query_start,
                    query_end=max(last.query_end, current.query_end),
                    source_start=last.source_start,
                    source_end=max(last.source_end, current.source_end),
                    matched_text=last.matched_text,
                    ngram_size=max(last.query_end, current.query_end) - last.query_start,
                    source_id=last.source_id,
                    source_name=last.source_name,
                    confidence=max(last.confidence, current.confidence),
                )
            else:
                merged.append(current)

        return merged

    def calculate_exact_score(self, matches: list[ExactMatch], total_words: int) -> float:
        """Calculate the percentage of text that is exactly matched."""
        if total_words == 0:
            return 0.0
        matched_words = set()
        for m in matches:
            for i in range(m.query_start, m.query_end):
                matched_words.add(i)
        return len(matched_words) / total_words * 100
