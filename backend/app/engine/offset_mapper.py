"""
Offset Mapper Engine
Builds structured document maps and merges overlapping highlight spans.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TokenMapping:
    text: str
    original_text: str
    start_char: int
    end_char: int
    word_index: int
    paragraph_index: int
    sentence_index: int
    page_number: int
    is_excluded: bool = False


@dataclass
class ParagraphMapping:
    paragraph_index: int
    start_char: int
    end_char: int
    text: str
    original_text: str
    page_number: int


@dataclass
class SentenceMapping:
    sentence_index: int
    paragraph_index: int
    start_char: int
    end_char: int
    text: str
    original_text: str
    word_count: int
    start_word: int
    end_word: int
    page_number: int


@dataclass
class ChunkMapping:
    chunk_id: int
    text: str
    original_text: str
    paragraph_index: int
    sentence_indices: List[int]
    start_char: int
    end_char: int
    start_word: int
    end_word: int
    word_count: int
    page_number: int
    source_document: str
    embedding: List[float] = field(default_factory=list)


@dataclass
class DocumentMap:
    source_filename: str
    full_text: str
    paragraphs: List[ParagraphMapping] = field(default_factory=list)
    sentences: List[SentenceMapping] = field(default_factory=list)
    tokens: List[TokenMapping] = field(default_factory=list)
    chunks: List[ChunkMapping] = field(default_factory=list)


@dataclass
class MatchSpan:
    start_char: int
    end_char: int
    matched_text: str
    original_text: str
    match_type: str  # "exact", "semantic", "high", "medium", "low"
    similarity: float
    source_index: int
    source_name: str
    source_chunk_id: int
    paragraph_index: int
    sentence_indices: List[int]
    page_number: int
    
    # Advanced Intelligence Fields
    group_type: str = "uncited_match"  # properly_cited, properly_quoted, missing_citation, weak_similarity, uncited_match
    confidence_score: float = 0.0
    is_whitelisted: bool = False
    citation_detected: bool = False
    semantic_weight: float = 1.0
    source_rank: int = 0
    integrity_flags: List[str] = field(default_factory=list)
    overlapping_sources: List[dict] = field(default_factory=list)
    top_source_id: str = ""
    weight: float = 1.0


class OffsetMapper:
    """Handles character-level offsets, document layout mapping, and span merging."""

    def __init__(self):
        self._nlp = None

    def _get_nlp(self):
        if self._nlp is None:
            import spacy
            try:
                self._nlp = spacy.load("en_core_web_sm", disable=["ner"])
            except OSError:
                self._nlp = False
        return self._nlp

    def build_document_map(self, full_text: str, paragraphs: List, source_filename: str) -> DocumentMap:
        """Create a hierarchical DocumentMap with precise character/word boundary indexes."""
        doc_map = DocumentMap(source_filename=source_filename, full_text=full_text)
        nlp = self._get_nlp()

        token_global_idx = 0
        sentence_global_idx = 0

        for p_info in paragraphs:
            p_map = ParagraphMapping(
                paragraph_index=p_info.paragraph_index,
                start_char=p_info.start_char,
                end_char=p_info.end_char,
                text=p_info.text.lower(),
                original_text=p_info.text,
                page_number=p_info.page_number
            )
            doc_map.paragraphs.append(p_map)

            p_text = p_info.text
            if nlp and nlp is not False:
                doc = nlp(p_text)
                p_sentences = [sent.text for sent in doc.sents]
            else:
                p_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', p_text) if s.strip()]

            current_search_idx = p_info.start_char
            for sent_text in p_sentences:
                idx = full_text.find(sent_text, current_search_idx)
                if idx == -1:
                    idx = current_search_idx
                
                start_char = idx
                end_char = idx + len(sent_text)
                current_search_idx = end_char

                if nlp and nlp is not False:
                    s_doc = nlp(sent_text)
                    words = [(t.text, t.idx) for t in s_doc if not t.is_space and not t.is_punct]
                else:
                    words = []
                    for m in re.finditer(r'\S+', sent_text):
                        words.append((m.group(), m.start()))

                sent_start_word = token_global_idx
                for word_text, word_rel_idx in words:
                    word_start = start_char + word_rel_idx
                    word_end = word_start + len(word_text)
                    
                    token = TokenMapping(
                        text=word_text.lower(),
                        original_text=word_text,
                        start_char=word_start,
                        end_char=word_end,
                        word_index=token_global_idx,
                        paragraph_index=p_info.paragraph_index,
                        sentence_index=sentence_global_idx,
                        page_number=p_info.page_number
                    )
                    doc_map.tokens.append(token)
                    token_global_idx += 1

                sent_end_word = token_global_idx

                sent_map = SentenceMapping(
                    sentence_index=sentence_global_idx,
                    paragraph_index=p_info.paragraph_index,
                    start_char=start_char,
                    end_char=end_char,
                    text=sent_text.lower(),
                    original_text=sent_text,
                    word_count=sent_end_word - sent_start_word,
                    start_word=sent_start_word,
                    end_word=sent_end_word,
                    page_number=p_info.page_number
                )
                doc_map.sentences.append(sent_map)
                sentence_global_idx += 1

        return doc_map

    def merge_spans_for_unique_coverage(self, match_spans: List[MatchSpan]) -> int:
        """
        Merge overlapping spans (ignoring sources and types) to compute the exact number of
        unique characters covered by plagiarism.
        Returns the total unique matched characters.
        """
        if not match_spans:
            return 0
        
        # Sort by start_char
        spans = sorted(match_spans, key=lambda s: s.start_char)
        merged = []
        
        for curr in spans:
            if not merged:
                merged.append([curr.start_char, curr.end_char])
                continue
            
            last = merged[-1]
            if curr.start_char <= last[1]:
                # Overlap, extend the end
                last[1] = max(last[1], curr.end_char)
            else:
                merged.append([curr.start_char, curr.end_char])
                
        return sum(end - start for start, end in merged)

    def deduplicate_source_spans(self, match_spans: List[MatchSpan]) -> List[MatchSpan]:
        """
        Merge overlapping spans WITHIN a single source to prevent duplicate counting.
        """
        if not match_spans:
            return []
            
        spans = sorted(match_spans, key=lambda s: (s.start_char, s.end_char))
        merged = []
        
        for curr in spans:
            if not merged:
                merged.append(curr)
                continue
                
            last = merged[-1]
            # If they overlap and belong to the same group type and match type
            if curr.start_char <= last.end_char and last.match_type == curr.match_type and last.group_type == curr.group_type:
                last.end_char = max(last.end_char, curr.end_char)
                last.similarity = max(last.similarity, curr.similarity)
            elif last.match_type == "exact" and curr.start_char <= last.end_char:
                # Prioritize exact match, just adjust curr start
                if curr.end_char > last.end_char:
                    # Adjust curr to start where last ended to avoid double counting visually
                    curr.start_char = last.end_char
                    merged.append(curr)
            else:
                merged.append(curr)
                
        return merged

    def merge_overlapping_spans_for_ui(self, match_spans: List[MatchSpan]) -> List[MatchSpan]:
        """
        Merge overlapping spans across ALL sources for the final frontend rendering.
        Ensures non-overlapping ranges, preserving the top source assignment and
        accumulating overlapping sources for Turnitin-style sidebar info.
        """
        if not match_spans:
            return []
            
        spans = sorted(match_spans, key=lambda s: (s.start_char, s.end_char))
        merged: List[MatchSpan] = []
        
        for curr in spans:
            if not merged:
                curr_copy = MatchSpan(
                    start_char=curr.start_char, end_char=curr.end_char,
                    matched_text=curr.matched_text, original_text=curr.original_text,
                    match_type=curr.match_type, similarity=curr.similarity,
                    source_index=curr.source_index, source_name=curr.source_name,
                    source_chunk_id=curr.source_chunk_id, paragraph_index=curr.paragraph_index,
                    sentence_indices=list(curr.sentence_indices), page_number=curr.page_number,
                    group_type=curr.group_type, confidence_score=curr.confidence_score,
                    is_whitelisted=curr.is_whitelisted, citation_detected=curr.citation_detected,
                    semantic_weight=curr.semantic_weight, source_rank=curr.source_rank,
                    integrity_flags=list(curr.integrity_flags),
                    overlapping_sources=list(curr.overlapping_sources),
                    top_source_id=curr.top_source_id
                )
                merged.append(curr_copy)
                continue
                
            last = merged[-1]
            if curr.start_char < last.end_char:
                # Overlap detected! Determine which is the top match
                # Priority: 1. Match type exact > semantic, 2. Similarity, 3. Word count
                last_len = last.end_char - last.start_char
                curr_len = curr.end_char - curr.start_char
                
                last_is_exact = last.match_type == "exact"
                curr_is_exact = curr.match_type == "exact"
                
                if (curr_is_exact and not last_is_exact) or \
                   (curr_is_exact == last_is_exact and curr.similarity > last.similarity) or \
                   (curr_is_exact == last_is_exact and curr.similarity == last.similarity and curr_len > last_len):
                    # curr wins as the top source for the overlap region.
                    overlap_src = {"source_index": last.source_index, "source_name": last.source_name, "similarity": last.similarity, "match_type": last.match_type}
                    if overlap_src not in curr.overlapping_sources and last.source_index != curr.source_index:
                        curr.overlapping_sources.append(overlap_src)
                    for osrc in last.overlapping_sources:
                        if osrc not in curr.overlapping_sources and osrc["source_index"] != curr.source_index:
                            curr.overlapping_sources.append(osrc)
                            
                    if last.start_char < curr.start_char:
                        last.end_char = curr.start_char
                        last.matched_text = last.matched_text[:curr.start_char - last.start_char]
                        last.original_text = last.original_text[:curr.start_char - last.start_char]
                        curr_copy = MatchSpan(
                            start_char=curr.start_char, end_char=curr.end_char,
                            matched_text=curr.matched_text, original_text=curr.original_text,
                            match_type=curr.match_type, similarity=curr.similarity,
                            source_index=curr.source_index, source_name=curr.source_name,
                            source_chunk_id=curr.source_chunk_id, paragraph_index=curr.paragraph_index,
                            sentence_indices=list(curr.sentence_indices), page_number=curr.page_number,
                            group_type=curr.group_type, confidence_score=curr.confidence_score,
                            is_whitelisted=curr.is_whitelisted, citation_detected=curr.citation_detected,
                            semantic_weight=curr.semantic_weight, source_rank=curr.source_rank,
                            integrity_flags=list(curr.integrity_flags),
                            overlapping_sources=list(curr.overlapping_sources),
                            top_source_id=curr.top_source_id
                        )
                        merged.append(curr_copy)
                    else:
                        merged[-1] = MatchSpan(
                            start_char=curr.start_char, end_char=curr.end_char,
                            matched_text=curr.matched_text, original_text=curr.original_text,
                            match_type=curr.match_type, similarity=curr.similarity,
                            source_index=curr.source_index, source_name=curr.source_name,
                            source_chunk_id=curr.source_chunk_id, paragraph_index=curr.paragraph_index,
                            sentence_indices=list(curr.sentence_indices), page_number=curr.page_number,
                            group_type=curr.group_type, confidence_score=curr.confidence_score,
                            is_whitelisted=curr.is_whitelisted, citation_detected=curr.citation_detected,
                            semantic_weight=curr.semantic_weight, source_rank=curr.source_rank,
                            integrity_flags=list(curr.integrity_flags),
                            overlapping_sources=list(curr.overlapping_sources),
                            top_source_id=curr.top_source_id
                        )
                else:
                    # last wins as the top source
                    overlap_src = {"source_index": curr.source_index, "source_name": curr.source_name, "similarity": curr.similarity, "match_type": curr.match_type}
                    if overlap_src not in last.overlapping_sources and curr.source_index != last.source_index:
                        last.overlapping_sources.append(overlap_src)
                    for osrc in curr.overlapping_sources:
                        if osrc not in last.overlapping_sources and osrc["source_index"] != last.source_index:
                            last.overlapping_sources.append(osrc)
                            
                    if curr.end_char > last.end_char:
                        curr.start_char = last.end_char
                        curr.matched_text = curr.matched_text[last.end_char - curr.start_char:]
                        curr.original_text = curr.original_text[last.end_char - curr.start_char:]
                        curr_copy = MatchSpan(
                            start_char=curr.start_char, end_char=curr.end_char,
                            matched_text=curr.matched_text, original_text=curr.original_text,
                            match_type=curr.match_type, similarity=curr.similarity,
                            source_index=curr.source_index, source_name=curr.source_name,
                            source_chunk_id=curr.source_chunk_id, paragraph_index=curr.paragraph_index,
                            sentence_indices=list(curr.sentence_indices), page_number=curr.page_number,
                            group_type=curr.group_type, confidence_score=curr.confidence_score,
                            is_whitelisted=curr.is_whitelisted, citation_detected=curr.citation_detected,
                            semantic_weight=curr.semantic_weight, source_rank=curr.source_rank,
                            integrity_flags=list(curr.integrity_flags),
                            overlapping_sources=list(curr.overlapping_sources),
                            top_source_id=curr.top_source_id
                        )
                        merged.append(curr_copy)
            else:
                curr_copy = MatchSpan(
                    start_char=curr.start_char, end_char=curr.end_char,
                    matched_text=curr.matched_text, original_text=curr.original_text,
                    match_type=curr.match_type, similarity=curr.similarity,
                    source_index=curr.source_index, source_name=curr.source_name,
                    source_chunk_id=curr.source_chunk_id, paragraph_index=curr.paragraph_index,
                    sentence_indices=list(curr.sentence_indices), page_number=curr.page_number,
                    group_type=curr.group_type, confidence_score=curr.confidence_score,
                    is_whitelisted=curr.is_whitelisted, citation_detected=curr.citation_detected,
                    semantic_weight=curr.semantic_weight, source_rank=curr.source_rank,
                    integrity_flags=list(curr.integrity_flags),
                    overlapping_sources=list(curr.overlapping_sources),
                    top_source_id=curr.top_source_id
                )
                merged.append(curr_copy)
                
        return merged

    def calculate_unique_word_coverage(self, spans: List[MatchSpan], doc_map: DocumentMap) -> int:
        """
        Calculate unique token indices covered by all given match spans.
        Returns the number of unique covered tokens.
        """
        if not spans or not doc_map or not doc_map.tokens:
            return 0
            
        covered_indices = set()
        sorted_spans = sorted(spans, key=lambda s: s.start_char)
        span_idx = 0
        num_spans = len(sorted_spans)
        
        for token in doc_map.tokens:
            while span_idx < num_spans and sorted_spans[span_idx].end_char <= token.start_char:
                span_idx += 1
            
            temp_idx = span_idx
            while temp_idx < num_spans and sorted_spans[temp_idx].start_char < token.end_char:
                span = sorted_spans[temp_idx]
                if token.start_char < span.end_char and token.end_char > span.start_char:
                    covered_indices.add(token.word_index)
                    break
                temp_idx += 1
                
        return len(covered_indices)
