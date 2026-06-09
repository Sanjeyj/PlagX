"""
Text Chunking Engine
Implements sliding window, sentence-aware, and semantic chunking
with full offset metadata preservation.
"""

import logging
from app.engine.offset_mapper import ChunkMapping, DocumentMap

logger = logging.getLogger(__name__)


class TextChunker:
    """
    Chunking engine that splits documents into overlapping chunks
    while preserving exact position metadata for highlight mapping.
    """

    def __init__(self, chunk_size_words: int = 75, overlap_percent: float = 0.20):
        self.chunk_size = chunk_size_words
        self.overlap = overlap_percent

    def chunk_document(self, doc_map: DocumentMap) -> list[ChunkMapping]:
        """
        Primary chunking method: sentence-aware sliding window.
        Produces chunks that respect sentence boundaries and carry full offset metadata.
        """
        chunks = []
        chunk_id = 0

        # Collect all sentences with their metadata
        all_sentences = doc_map.sentences
        if not all_sentences:
            # Fallback: treat entire paragraphs as sentences
            return self._chunk_by_words(doc_map)

        overlap_words = int(self.chunk_size * self.overlap)
        current_sentences = []
        current_word_count = 0

        i = 0
        while i < len(all_sentences):
            sent = all_sentences[i]
            current_sentences.append(sent)
            current_word_count += sent.word_count

            # When we have enough words for a chunk
            if current_word_count >= self.chunk_size or i == len(all_sentences) - 1:
                chunk = self._build_chunk(chunk_id, current_sentences, doc_map)
                chunks.append(chunk)
                chunk_id += 1

                # Calculate overlap: keep last N words worth of sentences
                overlap_count = 0
                overlap_start = len(current_sentences) - 1
                while overlap_start > 0 and overlap_count < overlap_words:
                    overlap_count += current_sentences[overlap_start].word_count
                    overlap_start -= 1

                # Keep overlapping sentences
                current_sentences = current_sentences[overlap_start + 1:]
                current_word_count = sum(s.word_count for s in current_sentences)
            
            i += 1

        doc_map.chunks = chunks
        logger.info(f"Created {len(chunks)} chunks (size={self.chunk_size}, overlap={self.overlap})")
        return chunks

    def _build_chunk(self, chunk_id: int, sentences: list, doc_map: DocumentMap) -> ChunkMapping:
        """Build a ChunkMapping from a list of sentences."""
        text_parts = [s.text for s in sentences]
        original_parts = [s.original_text for s in sentences]
        text = " ".join(text_parts)
        original_text = " ".join(original_parts)

        return ChunkMapping(
            chunk_id=chunk_id,
            text=text.lower(),
            original_text=original_text,
            paragraph_index=sentences[0].paragraph_index,
            sentence_indices=[s.sentence_index for s in sentences],
            start_char=sentences[0].start_char,
            end_char=sentences[-1].end_char,
            start_word=sentences[0].start_word,
            end_word=sentences[-1].end_word,
            word_count=sum(s.word_count for s in sentences),
            page_number=sentences[0].page_number,
            source_document=doc_map.source_filename,
        )

    def _chunk_by_words(self, doc_map: DocumentMap) -> list[ChunkMapping]:
        """Fallback word-level sliding window chunking."""
        chunks = []
        tokens = doc_map.tokens
        if not tokens:
            return chunks

        overlap_count = int(self.chunk_size * self.overlap)
        step = max(1, self.chunk_size - overlap_count)
        chunk_id = 0

        for start_idx in range(0, len(tokens), step):
            end_idx = min(start_idx + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start_idx:end_idx]
            if not chunk_tokens:
                break

            text = " ".join(t.text for t in chunk_tokens)
            original = " ".join(t.original_text for t in chunk_tokens)
            sent_indices = list(set(t.sentence_index for t in chunk_tokens))

            chunk = ChunkMapping(
                chunk_id=chunk_id,
                text=text,
                original_text=original,
                paragraph_index=chunk_tokens[0].paragraph_index,
                sentence_indices=sent_indices,
                start_char=chunk_tokens[0].start_char,
                end_char=chunk_tokens[-1].end_char,
                start_word=chunk_tokens[0].word_index,
                end_word=chunk_tokens[-1].word_index,
                word_count=len(chunk_tokens),
                page_number=chunk_tokens[0].page_number,
                source_document=doc_map.source_filename,
            )
            chunks.append(chunk)
            chunk_id += 1

            if end_idx >= len(tokens):
                break

        doc_map.chunks = chunks
        return chunks
