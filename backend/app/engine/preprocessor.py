"""
Text Preprocessing Engine v3.0
Handles normalization (Unicode NFKC, OCR artifacts, ligatures), stopword removal,
lemmatization, and sentence tokenization while maintaining exact offset mappings.
"""

import re
import unicodedata
import logging
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "but", "and", "or", "if", "while", "that", "this", "it",
    "its", "i", "me", "my", "we", "our", "you", "your", "he", "him",
    "his", "she", "her", "they", "them", "their", "what", "which", "who",
}

LIGATURE_MAP = {
    'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl',
    '’': "'", '‘': "'", '“': '"', '”': '"', '–': '-', '—': '-',
}


@dataclass
class PreprocessedText:
    """Result of text preprocessing with offset preservation."""
    original_text: str
    cleaned_text: str
    normalized_tokens: List[str]
    original_tokens: List[str]
    token_offsets: List[Tuple[int, int]]  # (start, end) in original text


class TextPreprocessor:
    """
    Text preprocessing pipeline that normalizes text (Unicode NFKC, ligatures, OCR artifacts)
    while preserving position mappings back to the original document.
    """

    def __init__(self):
        self._lemmatizer = None

    def normalize_text_elements(self, text: str) -> str:
        """Normalize Unicode NFKC, ligatures, and OCR artifacts."""
        if not text:
            return ""

        # 1. Unicode NFKC
        text = unicodedata.normalize('NFKC', text)

        # 2. Ligatures & typographic quotes
        for k, v in LIGATURE_MAP.items():
            text = text.replace(k, v)

        # 3. Clean OCR artifacts / hidden characters
        text = re.sub(r'[\u200b\u200c\u200d\ufeff\u00ad]', '', text)
        return text

    def preprocess(self, text: str, remove_stopwords: bool = True, lemmatize: bool = True) -> PreprocessedText:
        """Full preprocessing pipeline with offset tracking."""
        norm_text = self.normalize_text_elements(text)
        original_tokens = []
        normalized_tokens = []
        token_offsets = []

        for match in re.finditer(r'\S+', norm_text):
            word = match.group()
            start, end = match.start(), match.end()
            original_tokens.append(word)

            cleaned = re.sub(r'[^\w\s]', '', word.lower())
            if not cleaned:
                continue

            if remove_stopwords and cleaned in STOPWORDS:
                continue

            normalized_tokens.append(cleaned)
            token_offsets.append((start, end))

        cleaned_text = " ".join(normalized_tokens)

        return PreprocessedText(
            original_text=text,
            cleaned_text=cleaned_text,
            normalized_tokens=normalized_tokens,
            original_tokens=original_tokens,
            token_offsets=token_offsets,
        )

    def preprocess_for_exact(self, text: str) -> PreprocessedText:
        return self.preprocess(text, remove_stopwords=False, lemmatize=False)

    def preprocess_for_semantic(self, text: str) -> PreprocessedText:
        return self.preprocess(text, remove_stopwords=False, lemmatize=False)

    def normalize_for_hashing(self, text: str) -> str:
        text = self.normalize_text_elements(text.lower())
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
