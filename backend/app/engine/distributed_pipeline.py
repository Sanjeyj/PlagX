"""
Distributed Pipeline Engine for Celery task chains.
Splits the monolithic PlagiarismPipeline into discrete, cacheable stages.
"""

import uuid
import logging
import numpy as np
from dataclasses import asdict
from typing import Dict, Any, List

from app.engine.extractor import TextExtractor
from app.engine.offset_mapper import OffsetMapper, DocumentMap, ParagraphMapping, SentenceMapping, TokenMapping, MatchSpan, ChunkMapping
from app.engine.preprocessor import TextPreprocessor
from app.engine.chunker import TextChunker
from app.engine.citation_excluder import CitationExcluder
from app.engine.exact_match import ExactMatchEngine
from app.engine.semantic import SemanticEngine
from app.engine.vector_store import VectorStore
from app.engine.scorer import HybridScorer, AdaptiveThresholds
from app.engine.ai_detector import AIDetector
from app.config import get_settings
from app.engine.pipeline import SourceInfo, PlagiarismResult

settings = get_settings()
logger = logging.getLogger(__name__)

SOURCE_COLORS = ["#EF4444", "#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4", "#F97316"]

class DistributedPipeline:
    def __init__(self, db_session=None):
        self.db = db_session
        self.extractor = TextExtractor()
        self.mapper = OffsetMapper()
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
        self.ai_detector = AIDetector()
        self.vector_store.load("corpus")

    async def run_stage_extraction(self, document_id: str, file_path: str) -> Dict[str, Any]:
        """Stage 1: Extractor & Offset Mapper."""
        logger.info(f"[Stage 1] Extracting {document_id}")
        extraction = self.extractor.extract(file_path)
        
        doc_map = self.mapper.build_document_map(
            extraction.full_text, extraction.paragraphs, extraction.source_filename
        )
        
        # Serialize to dict for caching
        return {
            "document_id": document_id,
            "full_text": extraction.full_text,
            "source_filename": extraction.source_filename,
            "total_words": extraction.total_words,
            "total_pages": extraction.total_pages,
            "paragraphs": [asdict(p) for p in doc_map.paragraphs],
            "sentences": [asdict(s) for s in doc_map.sentences],
            "tokens": [asdict(t) for t in doc_map.tokens],
        }

    async def run_stage_embeddings(self, document_id: str, extraction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Chunking & Embeddings."""
        logger.info(f"[Stage 2] Embeddings for {document_id}")
        
        doc_map = DocumentMap(
            source_filename=extraction_data["source_filename"],
            full_text=extraction_data["full_text"],
            paragraphs=[ParagraphMapping(**p) for p in extraction_data["paragraphs"]],
            sentences=[SentenceMapping(**s) for s in extraction_data["sentences"]],
            tokens=[TokenMapping(**t) for t in extraction_data["tokens"]],
        )
        
        chunks = self.chunker.chunk_document(doc_map)
        if not chunks:
            return {"active_chunks": [], "query_embeddings": [], "citation_spans": [], "bib_start": None, "exclusion_stats": {}}
            
        bib_start = self.citation_excluder.find_bibliography_boundary(doc_map.full_text)
        citation_spans = self.citation_excluder.find_citation_spans(doc_map.full_text)
        exclusion_stats = self.citation_excluder.get_exclusion_stats(doc_map.full_text)
        
        active_chunks = []
        for chunk in chunks:
            excluded, _ = self.citation_excluder.should_exclude_chunk(
                chunk.start_char, chunk.end_char, chunk.text, bib_start, citation_spans
            )
            if not excluded:
                active_chunks.append(chunk)
                
        if active_chunks:
            chunk_texts = [c.text for c in active_chunks]
            query_embeddings = self.semantic_engine.generate_embeddings(chunk_texts)
        else:
            query_embeddings = []
            
        return {
            "active_chunks": [asdict(c) for c in active_chunks],
            "query_embeddings": query_embeddings.tolist() if hasattr(query_embeddings, 'tolist') else list(query_embeddings),
            "citation_spans": citation_spans,
            "bib_start": bib_start,
            "exclusion_stats": exclusion_stats,
        }

    def _word_to_char(self, word_idx: int, doc_map: DocumentMap, end: bool = False) -> int:
        if word_idx < len(doc_map.tokens):
            token = doc_map.tokens[word_idx]
            return token.end_char if end else token.start_char
        if doc_map.tokens:
            return doc_map.tokens[-1].end_char
        return 0

    def _char_to_paragraph(self, char_offset: int, doc_map: DocumentMap) -> int:
        for p in doc_map.paragraphs:
            if p.start_char <= char_offset < p.end_char:
                return p.paragraph_index
        return 0

    async def run_stage_semantic(self, document_id: str, extraction_data: Dict[str, Any], embedding_data: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 3: FAISS Semantic Search + Exact Matches."""
        logger.info(f"[Stage 3] Semantic Analysis for {document_id}")
        
        doc_map = DocumentMap(
            source_filename=extraction_data["source_filename"],
            full_text=extraction_data["full_text"],
            paragraphs=[ParagraphMapping(**p) for p in extraction_data["paragraphs"]],
            sentences=[SentenceMapping(**s) for s in extraction_data["sentences"]],
            tokens=[TokenMapping(**t) for t in extraction_data["tokens"]],
        )
        
        query_embeddings = np.array(embedding_data["query_embeddings"])
        active_chunks = [ChunkMapping(**c) for c in embedding_data["active_chunks"]]
        citation_spans = embedding_data["citation_spans"]
        bib_start = embedding_data["bib_start"]
        
        all_match_spans: list[MatchSpan] = []
        source_map: dict[str, SourceInfo] = {}
        
        if self.vector_store.total_vectors > 0 and len(query_embeddings) > 0:
            # Semantic search
            search_results = self.vector_store.search(query_embeddings, k=3, exclude_doc_id=document_id)
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
                    
                    if is_whitelisted:
                        continue
                        
                    weight = 0.8 if match_type == "high" else 0.5 if match_type == "medium" else 0.2
                        
                    src_id = meta.document_id
                    if src_id not in source_map:
                        source_map[src_id] = SourceInfo(
                            source_index=len(source_map),
                            source_id=src_id,
                            source_name=meta.document_name,
                            match_percentage=0,
                            color=SOURCE_COLORS[len(source_map) % len(SOURCE_COLORS)],
                        )
                        
                    span = MatchSpan(
                        start_char=chunk.start_char, end_char=chunk.end_char,
                        matched_text=chunk.text, original_text=chunk.original_text,
                        match_type=match_type, similarity=float(score),
                        source_index=source_map[src_id].source_index,
                        source_name=meta.document_name, source_chunk_id=meta.chunk_id,
                        paragraph_index=chunk.paragraph_index,
                        sentence_indices=chunk.sentence_indices, page_number=chunk.page_number,
                        group_type=group_type, confidence_score=float(score),
                        is_whitelisted=False, semantic_weight=weight,
                    )
                    all_match_spans.append(span)
                    source_map[src_id].matched_spans.append(span)
                    source_map[src_id].semantic_matches += 1

            # Exact search (only against retrieved sources to save time)
            query_words = extraction_data["full_text"].lower().split()
            for src_id in list(source_map.keys()):
                src_chunks = [m for m in self.vector_store._metadata if m.document_id == src_id]
                if not src_chunks:
                    continue
                src_words = " ".join(m.text for m in src_chunks).split()
                exact_matches = self.exact_engine.find_matches(
                    query_words, src_words,
                    source_id=src_id,
                    source_name=source_map[src_id].source_name,
                )
                if exact_matches:
                    for em in exact_matches:
                        start_char = self._word_to_char(em.query_start, doc_map)
                        end_char = self._word_to_char(em.query_end - 1, doc_map, end=True)
                        
                        group_type, is_whitelisted = self.citation_excluder.classify_match_span(
                            start_char, end_char, em.matched_text, bib_start, citation_spans,
                            semantic_confidence=em.confidence, is_exact=True
                        )
                        
                        if is_whitelisted:
                            continue
                        
                        span = MatchSpan(
                            start_char=start_char, end_char=end_char,
                            matched_text=em.matched_text,
                            original_text=extraction_data["full_text"][start_char:end_char],
                            match_type="exact", similarity=em.confidence,
                            source_index=source_map[src_id].source_index,
                            source_name=source_map[src_id].source_name,
                            source_chunk_id=0,
                            paragraph_index=self._char_to_paragraph(start_char, doc_map),
                            sentence_indices=[], page_number=1,
                            group_type=group_type, confidence_score=1.0,
                            is_whitelisted=False, semantic_weight=1.0,
                        )
                        all_match_spans.append(span)
                        source_map[src_id].matched_spans.append(span)
                        source_map[src_id].exact_matches += 1

        # Deduplicate per source
        for src in source_map.values():
            src.matched_spans = self.mapper.deduplicate_source_spans(src.matched_spans)
            
        ui_merged_spans = self.mapper.merge_overlapping_spans_for_ui(all_match_spans)

        # Vector store update
        if query_embeddings is not None and len(query_embeddings) > 0:
            self.vector_store.add_vectors(
                query_embeddings, active_chunks, document_id, extraction_data["source_filename"]
            )
            self.vector_store.save("corpus")
            
        # Serialize back to dict
        source_map_dict = {
            k: {
                "source_index": v.source_index,
                "source_id": v.source_id,
                "source_name": v.source_name,
                "match_percentage": v.match_percentage,
                "color": v.color,
                "exact_matches": v.exact_matches,
                "semantic_matches": v.semantic_matches,
                "matched_spans": [asdict(s) for s in v.matched_spans]
            }
            for k, v in source_map.items()
        }

        return {
            "all_match_spans": [asdict(s) for s in all_match_spans],
            "ui_merged_spans": [asdict(s) for s in ui_merged_spans],
            "source_map": source_map_dict,
            "exclusion_stats": embedding_data["exclusion_stats"]
        }

    async def run_stage_scoring(self, document_id: str, extraction_data: Dict[str, Any], semantic_data: Dict[str, Any]) -> str:
        """Stage 4: Scoring & AI Detection."""
        logger.info(f"[Stage 4] Scoring for {document_id}")
        
        doc_map = DocumentMap(
            source_filename=extraction_data["source_filename"],
            full_text=extraction_data["full_text"],
            paragraphs=[ParagraphMapping(**p) for p in extraction_data["paragraphs"]],
            sentences=[SentenceMapping(**s) for s in extraction_data["sentences"]],
            tokens=[TokenMapping(**t) for t in extraction_data["tokens"]],
        )
        
        all_match_spans = [MatchSpan(**s) for s in semantic_data["all_match_spans"]]
        ui_merged_spans = [MatchSpan(**s) for s in semantic_data["ui_merged_spans"]]
        
        # Deserialize source_map correctly back to SourceInfo objects
        source_map = {}
        for k, v_dict in semantic_data["source_map"].items():
            spans = v_dict.pop("matched_spans")
            src = SourceInfo(**v_dict)
            src.matched_spans = [MatchSpan(**s) for s in spans]
            source_map[k] = src

        doc_type = AdaptiveThresholds.detect_document_type(extraction_data["full_text"])
        
        exact_only_spans = [s for s in all_match_spans if s.match_type == "exact" and s.group_type not in ("properly_cited", "properly_quoted", "bibliography")]
        semantic_only_spans = [s for s in all_match_spans if s.match_type != "exact" and s.group_type not in ("properly_cited", "properly_quoted", "bibliography")]
        
        exact_chars = self.mapper.merge_spans_for_unique_coverage(exact_only_spans)
        semantic_chars = self.mapper.merge_spans_for_unique_coverage(semantic_only_spans)
        
        total_chars = len(extraction_data["full_text"]) or 1
        exact_pct = (exact_chars / total_chars) * 100
        semantic_pct = (semantic_chars / total_chars) * 100
        density = self.scorer.calculate_source_density(ui_merged_spans, total_chars)

        for src in source_map.values():
            meaningful_spans = [s for s in src.matched_spans if s.group_type not in ("properly_cited", "properly_quoted", "bibliography", "weak_similarity")]
            src_chars = self.mapper.merge_spans_for_unique_coverage(meaningful_spans)
            src.match_percentage = round((src_chars / total_chars) * 100, 1)

        active_sources = [s for s in source_map.values() if s.match_percentage > 0]
        active_sources.sort(key=lambda x: x.match_percentage, reverse=True)
        for idx, src in enumerate(active_sources):
            src.source_index = idx

        matched_words = sum(
            len(extraction_data["full_text"][s.start_char:s.end_char].split())
            for s in ui_merged_spans if s.group_type not in ("properly_cited", "properly_quoted", "bibliography")
        )

        scoring = self.scorer.calculate_score(
            exact_score=exact_pct, semantic_score=semantic_pct,
            source_density=density, total_words=extraction_data["total_words"],
            matched_words=matched_words, source_count=len(active_sources),
            exact_match_count=sum(s.exact_matches for s in active_sources),
            semantic_match_count=sum(s.semantic_matches for s in active_sources),
            document_type=doc_type,
        )

        para_scores = self.scorer.calculate_paragraph_scores(doc_map.paragraphs, ui_merged_spans)

        integrity_flags = []
        if "\u200b" in extraction_data["full_text"] or "\u200c" in extraction_data["full_text"]:
            integrity_flags.append("Hidden zero-width characters detected")
        import re
        if re.search(r'[а-яА-Я]+', extraction_data["full_text"]) and re.search(r'[a-zA-Z]+', extraction_data["full_text"]):
            integrity_flags.append("Suspicious mixed script (Cyrillic + Latin) detected")
        if extraction_data["full_text"].count("  ") > len(extraction_data["full_text"]) * 0.05:
            integrity_flags.append("Suspicious whitespace inflation detected")

        para_dicts = [
            {"text": p.text, "start_char": p.start_char, "end_char": p.end_char}
            for p in doc_map.paragraphs
        ]
        ai_result = self.ai_detector.analyze(extraction_data["full_text"], para_dicts)

        result = PlagiarismResult(
            document_id=document_id,
            overall_score=scoring.overall_score,
            exact_score=scoring.exact_score,
            semantic_score=scoring.semantic_score,
            source_density_score=scoring.source_density_score,
            risk_level=scoring.risk_level,
            ai_probability=ai_result["ai_probability"],
            ai_confidence=ai_result["confidence_level"],
            ai_suspicious_spans=ai_result["suspicious_spans"],
            total_words=extraction_data["total_words"],
            total_pages=extraction_data["total_pages"],
            matched_words=matched_words,
            sources=active_sources,
            all_spans=ui_merged_spans,
            paragraph_scores=para_scores,
            document_map=doc_map,
            full_text=extraction_data["full_text"],
            exclusion_stats=semantic_data["exclusion_stats"],
            integrity_flags=integrity_flags,
        )
        
        # Save to DB
        from app.services.report_service import ReportService
        report_svc = ReportService()
        report = await report_svc.create_report(self.db, document_id, result, generate_pdf=False)
        return report.id
