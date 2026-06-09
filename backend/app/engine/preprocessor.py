"""
Text Preprocessing Engine
Handles normalization, stopword removal, lemmatization, and sentence tokenization
while maintaining offset mappings to the original text.
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Common English stopwords (avoiding spaCy dependency for basic operations)
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


@dataclass
class PreprocessedText:
    """Result of text preprocessing with offset preservation."""
    original_text: str
    cleaned_text: str
    normalized_tokens: list[str]
    original_tokens: list[str]
    token_offsets: list[tuple[int, int]]  # (start, end) in original text


class TextPreprocessor:
    """
    Text preprocessing pipeline that normalizes text while preserving
    position mappings back to the original document.
    """

    def __init__(self):
        self._lemmatizer = None

    def _get_lemmatizer(self):
        """Lazy-load spaCy for lemmatization."""
        if self._lemmatizer is None:
            try:
                import spacy
                self._lemmatizer = spacy.load("en_core_web_sm", disable=["ner", "parser"])
                logger.info("spaCy lemmatizer loaded")
            except OSError:
                logger.warning("spaCy model not found, using basic lemmatization")
                self._lemmatizer = False
        return self._lemmatizer

    def preprocess(self, text: str, remove_stopwords: bool = True, lemmatize: bool = True) -> PreprocessedText:
        """Full preprocessing pipeline with offset tracking."""
        original_tokens = []
        normalized_tokens = []
        token_offsets = []

        for match in re.finditer(r'\S+', text):
            word = match.group()
            start, end = match.start(), match.end()
            original_tokens.append(word)

            # Normalize
            cleaned = re.sub(r'[^\w\s]', '', word.lower())
            if not cleaned:
                continue

            if remove_stopwords and cleaned in STOPWORDS:
                continue

            if lemmatize:
                cleaned = self._lemmatize_word(cleaned)

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
        """Light preprocessing for exact matching (keep stopwords, no lemmatization)."""
        return self.preprocess(text, remove_stopwords=False, lemmatize=False)

    def preprocess_for_semantic(self, text: str) -> PreprocessedText:
        """Preprocessing for semantic matching (moderate cleaning)."""
        return self.preprocess(text, remove_stopwords=False, lemmatize=False)

    def _lemmatize_word(self, word: str) -> str:
        """Lemmatize a single word."""
        nlp = self._get_lemmatizer()
        if nlp and nlp is not False:
            doc = nlp(word)
            if doc:
                return doc[0].lemma_
        return word

    def normalize_for_hashing(self, text: str) -> str:
        """Normalize text for n-gram hashing (aggressive normalization)."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
