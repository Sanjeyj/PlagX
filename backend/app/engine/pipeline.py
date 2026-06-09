"""
Pipeline Orchestrator
Coordinates all engine components in the multi-stage plagiarism detection pipeline.
Extract → Preprocess → Chunk → Cite-Exclude → Exact Match → Semantic Match → Score → Map
"""

import logging
import uuid
import re
from dataclasses import dataclass, field
from typing import Optional

from app.config import get_settings
from app.engine.extractor import TextExtractor
from app.engine.offset_mapper import OffsetMapper, MatchSpan, DocumentMap
from app.engine.preprocessor import TextPreprocessor
from app.engine.chunker import TextChunker
from app.engine.citation_excluder import CitationExcluder
from app.engine.exact_match import ExactMatchEngine
from app.engine.semantic import SemanticEngine
from app.engine.vector_store import VectorStore
from app.engine.scorer import HybridScorer, AdaptiveThresholds
from app.engine.ai_detector import AIDetector

logger = logging.getLogger(__name__)
settings = get_settings()

# Source colors palette
SOURCE_COLORS = [
    "#EF4444", "#F97316", "#EAB308", "#22C55E", "#3B82F6",
    "#8B5CF6", "#EC4899", "#14B8A6", "#F43F5E", "#6366F1",
    "#D946EF", "#0EA5E9", "#84CC16", "#FF6B6B", "#4ECDC4",
]


@dataclass
class SourceInfo:
    """Aggregated source information."""
    source_index: int
    source_id: str
    source_name: str
    match_percentage: float
    color: str
    matched_spans: list[MatchSpan] = field(default_factory=list)
    exact_matches: int = 0
    semantic_matches: int = 0


@dataclass
class PlagiarismResult:
    """Complete plagiarism analysis result."""
    document_id: str
    overall_score: float
    exact_score: float
    semantic_score: float
    source_density_score: float
    risk_level: str
    total_words: int
    total_pages: int
    matched_words: int
    sources: list[SourceInfo] = field(default_factory=list)
    all_spans: list[MatchSpan] = field(default_factory=list)
    paragraph_scores: list[dict] = field(default_factory=list)
    document_map: Optional[DocumentMap] = None
    full_text: str = ""
    exclusion_stats: dict = field(default_factory=dict)
    ai_probability: float = 0.0
    ai_confidence: str = "Likely Human"
    ai_suspicious_spans: list[dict] = field(default_factory=list)
    integrity_flags: list[str] = field(default_factory=list)


class PlagiarismPipeline:
    """
    Multi-stage plagiarism detection pipeline.
    Stage 1: Text extraction + offset mapping
    Stage 2: Preprocessing + chunking
    Stage 3: Citation exclusion
    Stage 4: Exact n-gram matching
    Stage 5: Semantic embedding similarity
    Stage 6: Score aggregation + span merging
    """

    def __init__(self, db_session=None):
        self.db = db_session
        self.extractor = TextExtractor()
        self.mapper = OffsetMapper()
        self.preprocessor = TextPreprocessor()
        self.ai_detector = AIDetector()
        self.chunker = TextChunker(
            chunk_size_words=settings.CHUNK_SIZE_WORDS,
            overlap_percent=settings.CHUNK_OVERLAP_PERCENT,
        )
        self.citation_excluder = CitationExcluder()
        self.exact_engine = ExactMatchEngine(
            ngram_size=settings.NGRAM_SIZE,
            min_match_words=settings.MIN_EXACT_MATCH_WORDS,
        )
        self.semantic_engine = SemanticEngine(
            model_name=settings.SENTENCE_TRANSFORMER_MODEL,
            high_threshold=settings.SEMANTIC_HIGH_THRESHOLD,
            med_threshold=settings.SEMANTIC_MED_THRESHOLD,
            low_threshold=settings.SEMANTIC_LOW_THRESHOLD,
        )
        self.vector_store = VectorStore(store_dir=str(settings.vector_db_path))
        self.scorer = HybridScorer(
            exact_weight=settings.EXACT_MATCH_WEIGHT,
            semantic_weight=settings.SEMANTIC_MATCH_WEIGHT,
            density_weight=settings.SOURCE_DENSITY_WEIGHT,
        )
        # Load existing vector index
        self.vector_store.load("corpus")

    def run(self, file_path: str, document_id: str = None, progress_callback=None) -> PlagiarismResult:
        """Execute the full plagiarism detection pipeline."""
        doc_id = document_id or str(uuid.uuid4())

        def update_progress(stage: str, pct: int):
            if progress_callback:
                progress_callback(stage, pct)
            logger.info(f"[{stage}] {pct}%")

        # === STAGE 1: Extract text ===
        update_progress("Extracting text", 5)
        extraction = self.extractor.extract(file_path)

        # === STAGE 2: Build document map with offsets ===
        update_progress("Building document map", 10)
        doc_map = self.mapper.build_document_map(
            extraction.full_text, extraction.paragraphs, extraction.source_filename
        )
        self.citation_excluder.mark_exclusions(doc_map, extraction.full_text)

        # === STAGE 3: Chunk the document ===
        update_progress("Chunking document", 15)
        chunks = self.chunker.chunk_document(doc_map)

        if not chunks:
            return self._empty_result(doc_id, extraction)

        # === STAGE 4: Citation exclusion ===
        update_progress("Analyzing citations", 20)
        bib_start = self.citation_excluder.find_bibliography_boundary(extraction.full_text)
        citation_spans = self.citation_excluder.find_citation_spans(extraction.full_text)
        exclusion_stats = self.citation_excluder.get_exclusion_stats(extraction.full_text)

        # Filter out bibliography and citation chunks
        active_chunks = []
        for chunk in chunks:
            excluded, reason = self.citation_excluder.should_exclude_chunk(
                chunk.start_char, chunk.end_char, chunk.text,
                bib_start, citation_spans,
            )
            if not excluded:
                active_chunks.append(chunk)

        logger.info(f"Active chunks: {len(active_chunks)}/{len(chunks)} (excluded {len(chunks) - len(active_chunks)})")

        if not active_chunks:
            return self._empty_result(doc_id, extraction)

        # === STAGE 5: Generate embeddings ===
        update_progress("Generating embeddings", 30)
        import numpy as np
        query_texts = [c.text for c in active_chunks]
        query_embeddings = self.semantic_engine.encode(query_texts)

        # Store embeddings in chunks
        for i, chunk in enumerate(active_chunks):
            chunk.embedding = query_embeddings[i].tolist()

        # === STAGE 6: Exact matching against corpus ===
        update_progress("Running exact match", 45)
        raw_exact_spans = []
        query_words = extraction.full_text.lower().split()

        # Get source documents from vector store
        source_docs = self.vector_store.get_source_documents()
        for src_doc in source_docs:
            if src_doc["document_id"] == doc_id:
                continue
            src_chunks = [
                m for m in self.vector_store._metadata
                if m.document_id == src_doc["document_id"]
            ]
            if not src_chunks:
                continue
            src_words = " ".join(m.text for m in src_chunks).split()
            exact_matches = self.exact_engine.find_matches(
                query_words, src_words,
                source_id=src_doc["document_id"],
                source_name=src_doc["document_name"],
            )
            for em in exact_matches:
                start_char = self._word_to_char(em.query_start, doc_map)
                end_char = self._word_to_char(em.query_end - 1, doc_map, end=True)
                
                group_type, is_whitelisted = self.citation_excluder.classify_match_span(
                    start_char, end_char, em.matched_text, bib_start, citation_spans,
                    semantic_confidence=em.confidence, is_exact=True
                )
                
                span = MatchSpan(
                    start_char=start_char, end_char=end_char,
                    matched_text=em.matched_text,
                    original_text=extraction.full_text[start_char:end_char],
                    match_type="exact", similarity=em.confidence,
                    source_index=-1,
                    source_name=src_doc["document_name"],
                    source_chunk_id=0,
                    paragraph_index=self._char_to_paragraph(start_char, doc_map),
                    sentence_indices=[], page_number=1,
                    group_type=group_type,
                    confidence_score=1.0,
                    is_whitelisted=is_whitelisted,
                    semantic_weight=1.0,
                    top_source_id=src_doc["document_id"]
                )
                raw_exact_spans.append(span)

        # === STAGE 7: Semantic matching via FAISS ===
        update_progress("Running semantic analysis", 60)
        raw_semantic_spans = []
        if self.vector_store.total_vectors > 0:
            search_results = self.vector_store.search(
                query_embeddings, k=3, exclude_doc_id=doc_id,
            )
            for q_idx, results in enumerate(search_results):
                chunk = active_chunks[q_idx]
                for meta, score in results:
                    match_type = self.semantic_engine.classify_match_type(score)
                    if match_type == "none":
                        continue
                        
                    group_type, is_whitelisted = self.citation_excluder.classify_match_span(
                        chunk.start_char, chunk.end_char, chunk.text, bib_start, citation_spans,
                        semantic_confidence=float(score), is_exact=False
                    )
                    
                    # Semantic weight
                    if match_type == "high":
                        weight = 0.8
                    elif match_type == "medium":
                        weight = 0.5
                    else:
                        weight = 0.2
                        
                    span = MatchSpan(
                        start_char=chunk.start_char, end_char=chunk.end_char,
                        matched_text=chunk.text,
                        original_text=chunk.original_text,
                        match_type=match_type, similarity=float(score),
                        source_index=-1,
                        source_name=meta.document_name,
                        source_chunk_id=meta.chunk_id,
                        paragraph_index=chunk.paragraph_index,
                        sentence_indices=chunk.sentence_indices,
                        page_number=chunk.page_number,
                        group_type=group_type,
                        confidence_score=float(score),
                        is_whitelisted=is_whitelisted,
                        semantic_weight=weight,
                        top_source_id=meta.document_id
                    )
                    raw_semantic_spans.append(span)

        # === STAGE 8: Sweep-Line Deduplication & Dominant Source Selection ===
        update_progress("Deduplicating sources", 75)
        
        all_raw_spans = raw_exact_spans + raw_semantic_spans
        num_tokens = len(doc_map.tokens)
        
        # Precompute static span properties for performance optimization (Step 8/13)
        for s in all_raw_spans:
            s.word_count = len(s.matched_text.split())
            s.is_full_sentence = False
            for sent in doc_map.sentences:
                if s.start_char <= sent.start_char + 5 and s.end_char >= sent.end_char - 5:
                    s.is_full_sentence = True
                    break
        
        def get_base_weight(group_type: str, match_type: str, similarity: float) -> float:
            if group_type == "bibliography":
                return 0.0
            if group_type == "boilerplate":
                return 0.0
            if group_type in ("cited_and_quoted", "properly_cited", "properly_quoted"):
                return 0.05
            if group_type == "weak_overlap":
                return 0.10
            
            # Otherwise uncited
            if match_type == "exact":
                if group_type == "missing_quotation":
                    return 0.8
                if group_type == "missing_citation":
                    return 0.6
                return 1.0
            else: # semantic
                if similarity >= 0.80:
                    return 0.6
                return 0.10

        # 1. Sweep-line interval creation
        class SweepEvent:
            def __init__(self, offset: int, is_start: bool, span):
                self.offset = offset
                self.is_start = is_start
                self.span = span
                
        events = []
        for span in all_raw_spans:
            events.append(SweepEvent(span.start_char, True, span))
            events.append(SweepEvent(span.end_char, False, span))
            
        events.sort(key=lambda e: (e.offset, 0 if not e.is_start else 1))
        
        active_raw_spans = []
        disjoint_intervals = []
        last_offset = 0
        token_ptr = 0
        
        for event in events:
            current_offset = event.offset
            if current_offset > last_offset and active_raw_spans:
                # Select dominant span using weighted priorities
                def get_span_priority(s):
                    base_w = get_base_weight(s.group_type, s.match_type, s.similarity)
                    # Length/continuity
                    span_words = s.word_count
                    
                    if s.is_full_sentence:
                        continuity = 0.95
                    elif span_words < 10:
                        continuity = 0.4
                    elif span_words < 15:
                        continuity = 0.6
                    elif span_words < 25:
                        continuity = 0.8
                    else:
                        continuity = 1.0
                        
                    # Citation absence
                    if s.group_type == "uncited_overlap":
                        citation_fac = 1.0
                    elif s.group_type in ("missing_quotation", "missing_citation"):
                        citation_fac = 0.8
                    else:
                        citation_fac = 0.1
                        
                    # Overlap reinforcement
                    overlaps_count = sum(1 for os in active_raw_spans if os.top_source_id != s.top_source_id)
                    reinforcement = 1.0 + 0.1 * min(overlaps_count, 3)
                    
                    confidence = continuity * citation_fac * reinforcement * (1.0 if s.match_type == "exact" else s.similarity)
                    weight = base_w * confidence
                    return (weight, 1 if s.match_type == "exact" else 0, s.similarity, s.end_char - s.start_char)
                
                # Optimize winner selection and unpack priority values
                winner = None
                best_priority = None
                for s in active_raw_spans:
                    priority = get_span_priority(s)
                    if best_priority is None or priority > best_priority:
                        best_priority = priority
                        winner = s
                        
                weight_val, is_exact, sim_val, _ = best_priority
                
                # Check semantic uniqueness (Step 6)
                is_weak_semantic = (winner.match_type != "exact" and sim_val < 0.80)
                is_reinforced = sum(1 for os in active_raw_spans if os.top_source_id != winner.top_source_id) > 0
                words_count = winner.word_count
                is_generic = is_weak_semantic and (words_count < 15) and not is_reinforced
                
                # Check if this interval overlaps with any excluded tokens
                is_excluded_interval = False
                while token_ptr < num_tokens and doc_map.tokens[token_ptr].end_char <= last_offset:
                    token_ptr += 1
                temp_ptr = token_ptr
                while temp_ptr < num_tokens and doc_map.tokens[temp_ptr].start_char < current_offset:
                    if doc_map.tokens[temp_ptr].is_excluded:
                        is_excluded_interval = True
                        break
                    temp_ptr += 1
                
                if is_excluded_interval:
                    weight_val = 0.0
                
                if not is_generic and weight_val > 0.0:
                    disjoint_intervals.append({
                        "start": last_offset,
                        "end": current_offset,
                        "dominant": winner,
                        "all": list(active_raw_spans),
                        "weight": weight_val
                    })
                    
            if event.is_start:
                active_raw_spans.append(event.span)
            else:
                for idx, item in enumerate(active_raw_spans):
                    if item is event.span:
                        active_raw_spans.pop(idx)
                        break
            last_offset = current_offset
            
        # 2. Merge disjoint intervals into finalized MatchSpans (Step 7)
        merged_spans = []
        current_span = None
        
        for interval in disjoint_intervals:
            start = interval["start"]
            end = interval["end"]
            dom = interval["dominant"]
            wt = interval["weight"]
            
            # Extract overlapping sources (Step 5/10)
            over_list = []
            seen_ids = {dom.top_source_id}
            for s in interval["all"]:
                if s.top_source_id not in seen_ids:
                    seen_ids.add(s.top_source_id)
                    over_list.append({
                        "source_id": s.top_source_id,
                        "source_name": s.source_name,
                        "match_type": s.match_type,
                        "similarity": s.similarity
                    })
                    
            if current_span is None:
                current_span = MatchSpan(
                    start_char=start,
                    end_char=end,
                    matched_text=extraction.full_text[start:end],
                    original_text=extraction.full_text[start:end],
                    match_type=dom.match_type,
                    similarity=dom.similarity,
                    source_index=-1,
                    source_name=dom.source_name,
                    source_chunk_id=dom.source_chunk_id,
                    paragraph_index=dom.paragraph_index,
                    sentence_indices=list(dom.sentence_indices),
                    page_number=dom.page_number,
                    group_type=dom.group_type,
                    confidence_score=dom.confidence_score,
                    is_whitelisted=dom.is_whitelisted,
                    citation_detected=dom.citation_detected,
                    semantic_weight=dom.semantic_weight,
                    overlapping_sources=over_list,
                    top_source_id=dom.top_source_id,
                    weight=wt
                )
            else:
                char_gap = start - current_span.end_char
                # Do not merge across paragraphs (Step 7)
                # Max gap is 10 characters (Step 7)
                if (current_span.top_source_id == dom.top_source_id and
                    current_span.group_type == dom.group_type and
                    current_span.match_type == dom.match_type and
                    current_span.paragraph_index == dom.paragraph_index and
                    char_gap <= 10):
                    current_span.end_char = end
                    current_span.matched_text = extraction.full_text[current_span.start_char:end]
                    current_span.original_text = current_span.matched_text
                    current_span.similarity = max(current_span.similarity, dom.similarity)
                    current_span.weight = max(current_span.weight, wt)
                    
                    # Merge overlapping sources
                    existing_ids = {o["source_id"] for o in current_span.overlapping_sources}
                    for o in over_list:
                        if o["source_id"] not in existing_ids:
                            current_span.overlapping_sources.append(o)
                else:
                    merged_spans.append(current_span)
                    current_span = MatchSpan(
                        start_char=start,
                        end_char=end,
                        matched_text=extraction.full_text[start:end],
                        original_text=extraction.full_text[start:end],
                        match_type=dom.match_type,
                        similarity=dom.similarity,
                        source_index=-1,
                        source_name=dom.source_name,
                        source_chunk_id=dom.source_chunk_id,
                        paragraph_index=dom.paragraph_index,
                        sentence_indices=list(dom.sentence_indices),
                        page_number=dom.page_number,
                        group_type=dom.group_type,
                        confidence_score=dom.confidence_score,
                        is_whitelisted=dom.is_whitelisted,
                        citation_detected=dom.citation_detected,
                        semantic_weight=dom.semantic_weight,
                        overlapping_sources=over_list,
                        top_source_id=dom.top_source_id,
                        weight=wt
                    )
                    
        if current_span is not None:
            merged_spans.append(current_span)
            
        # Filter finalized spans and apply boundary trimming (Step 7/11)
        finalized_spans = []
        for span in merged_spans:
            if span.weight <= 0.0:
                continue
                
            # Trim leading/trailing whitespace/punctuation from boundaries
            start = span.start_char
            end = span.end_char
            while start < end and not extraction.full_text[start].isalnum():
                start += 1
            while end > start and not extraction.full_text[end - 1].isalnum():
                end -= 1
                
            if start >= end:
                continue
                
            span.start_char = start
            span.end_char = end
            span.matched_text = extraction.full_text[start:end]
            span.original_text = span.matched_text
            
            span_words = len(span.matched_text.split())
            if span.match_type == "exact" and span_words < 8:
                continue
            if span.match_type != "exact" and span_words < 12:
                continue
            if self.citation_excluder.should_exclude_span(span.start_char, span.end_char, span.matched_text, bib_start):
                continue
            finalized_spans.append(span)

        # === STAGE 9: Calculate scores & Map sources ===
        update_progress("Calculating scores", 85)
        doc_type = AdaptiveThresholds.detect_document_type(extraction.full_text)
        total_words = len(doc_map.tokens) or 1
        
        token_weights = [0.0] * num_tokens
        token_owners = [None] * num_tokens
        
        # Sort finalized spans (should be sorted/disjoint already, but let's be safe)
        finalized_spans.sort(key=lambda s: s.start_char)
        
        # Build token coverage in O(S + T) linear scan optimization (Step 13)
        span_idx = 0
        num_spans = len(finalized_spans)
        
        for t_idx, token in enumerate(doc_map.tokens):
            if token.is_excluded:
                continue
                
            # Advance span_idx while the current span ends before token start
            while span_idx < num_spans and finalized_spans[span_idx].end_char <= token.start_char:
                span_idx += 1
                
            # Check overlap with any span starting before token end
            temp_idx = span_idx
            while temp_idx < num_spans and finalized_spans[temp_idx].start_char < token.end_char:
                span = finalized_spans[temp_idx]
                if token.start_char < span.end_char and token.end_char > span.start_char:
                    if span.weight > token_weights[t_idx]:
                        token_weights[t_idx] = span.weight
                        token_owners[t_idx] = span
                temp_idx += 1
                        
        total_weighted_matched = sum(token_weights)
        
        used_source_ids = set()
        for span in finalized_spans:
            used_source_ids.add(span.top_source_id)
            for osrc in span.overlapping_sources:
                used_source_ids.add(osrc["source_id"])
                
        source_names_map = {}
        for span in all_raw_spans:
            source_names_map[span.top_source_id] = span.source_name
        for src_doc in source_docs:
            source_names_map[src_doc["document_id"]] = src_doc["document_name"]
            
        active_sources = []
        for src_id in used_source_ids:
            src_weighted_sum = 0.0
            for t_idx in range(num_tokens):
                owner = token_owners[t_idx]
                if owner is not None and owner.top_source_id == src_id:
                    src_weighted_sum += token_weights[t_idx]
                    
            raw_src_pct = (src_weighted_sum / total_words) * 100.0
            pct = self.scorer.normalize_score(raw_src_pct)
            
            top_spans = [s for s in finalized_spans if s.top_source_id == src_id]
            exact_count = sum(1 for s in top_spans if s.match_type == "exact")
            semantic_count = sum(1 for s in top_spans if s.match_type != "exact")
            
            if pct > 0.0 or len(top_spans) > 0:
                active_sources.append(SourceInfo(
                    source_index=-1,
                    source_id=src_id,
                    source_name=source_names_map.get(src_id, "Unknown Source"),
                    match_percentage=pct,
                    color="",
                    matched_spans=top_spans,
                    exact_matches=exact_count,
                    semantic_matches=semantic_count
                ))
                
        active_sources.sort(key=lambda x: x.match_percentage, reverse=True)
        
        source_id_to_idx = {}
        for idx, src in enumerate(active_sources):
            src.source_index = idx
            src.color = SOURCE_COLORS[idx % len(SOURCE_COLORS)]
            source_id_to_idx[src.source_id] = idx
            
        for span in finalized_spans:
            span.source_index = source_id_to_idx.get(span.top_source_id, -1)
            for osrc in span.overlapping_sources:
                osrc["source_index"] = source_id_to_idx.get(osrc["source_id"], -1)
                
        exact_weighted_sum = 0.0
        semantic_weighted_sum = 0.0
        for t_idx in range(num_tokens):
            owner = token_owners[t_idx]
            if owner is not None:
                if owner.match_type == "exact":
                    exact_weighted_sum += token_weights[t_idx]
                else:
                    semantic_weighted_sum += token_weights[t_idx]
                    
        exact_pct = round((exact_weighted_sum / total_words) * 100.0, 1)
        semantic_pct = round((semantic_weighted_sum / total_words) * 100.0, 1)
        
        source_density = self.scorer.calculate_source_density(len(active_sources), total_words)
        
        scoring = self.scorer.calculate_score(
            exact_score=exact_pct, semantic_score=semantic_pct,
            source_density=source_density, total_words=total_words,
            matched_words=total_weighted_matched, source_count=len(active_sources),
            exact_match_count=sum(s.exact_matches for s in active_sources),
            semantic_match_count=sum(s.semantic_matches for s in active_sources),
            document_type=doc_type,
        )
        
        ui_merged_spans = self.mapper.merge_overlapping_spans_for_ui(finalized_spans)
        
        para_scores = self.scorer.calculate_paragraph_scores(
            doc_map.paragraphs, ui_merged_spans,
        )

        # === STAGE 9.3: Integrity Engine ===
        update_progress("Running integrity analysis", 87)
        integrity_flags = []
        if "\u200b" in extraction.full_text or "\u200c" in extraction.full_text:
            integrity_flags.append("Hidden zero-width characters detected")
        if re.search(r'[а-яА-Я]+', extraction.full_text) and re.search(r'[a-zA-Z]+', extraction.full_text):
            # Very basic Cyrillic homoglyph check
            integrity_flags.append("Suspicious mixed script (Cyrillic + Latin) detected")
        if extraction.full_text.count("  ") > len(extraction.full_text) * 0.05:
            integrity_flags.append("Suspicious whitespace inflation detected")

        # === STAGE 9.5: AI Detection ===
        update_progress("Running AI detection", 88)
        para_dicts = [
            {"text": p.text, "start_char": p.start_char, "end_char": p.end_char}
            for p in doc_map.paragraphs
        ]
        ai_result = self.ai_detector.analyze(extraction.full_text, para_dicts)

        # === STAGE 10: Add document to corpus ===
        update_progress("Updating corpus", 90)
        self.vector_store.add_vectors(
            query_embeddings, active_chunks, doc_id, extraction.source_filename,
        )
        self.vector_store.save("corpus")

        update_progress("Complete", 100)

        return PlagiarismResult(
            document_id=doc_id,
            overall_score=scoring.overall_score,
            exact_score=scoring.exact_score,
            semantic_score=scoring.semantic_score,
            source_density_score=scoring.source_density_score,
            risk_level=scoring.risk_level,
            ai_probability=ai_result["ai_probability"],
            ai_confidence=ai_result["confidence_level"],
            ai_suspicious_spans=ai_result["suspicious_spans"],
            total_words=extraction.total_words,
            total_pages=extraction.total_pages,
            matched_words=int(total_weighted_matched),
            sources=active_sources,
            all_spans=ui_merged_spans,
            paragraph_scores=para_scores,
            document_map=doc_map,
            full_text=extraction.full_text,
            exclusion_stats=exclusion_stats,
            integrity_flags=integrity_flags,
        )

    def _word_to_char(self, word_idx: int, doc_map: DocumentMap, end: bool = False) -> int:
        """Convert word index to character offset."""
        if word_idx < len(doc_map.tokens):
            token = doc_map.tokens[word_idx]
            return token.end_char if end else token.start_char
        if doc_map.tokens:
            return doc_map.tokens[-1].end_char
        return 0

    def _char_to_paragraph(self, char_offset: int, doc_map: DocumentMap) -> int:
        """Find paragraph index for a character offset."""
        for p in doc_map.paragraphs:
            if p.start_char <= char_offset < p.end_char:
                return p.paragraph_index
        return 0

    def _empty_result(self, doc_id: str, extraction) -> PlagiarismResult:
        return PlagiarismResult(
            document_id=doc_id, overall_score=0, exact_score=0,
            semantic_score=0, source_density_score=0, risk_level="low",
            total_words=extraction.total_words, total_pages=extraction.total_pages,
            matched_words=0, full_text=extraction.full_text,
        )
