"""
Comprehensive Phase 14 Benchmark & Regression Test Suite for PlagX Enterprise Similarity Engine v2
"""

unittest_imports = True
import unittest
import os
import sys

from app.engine.exact_match import ExactMatchEngine, ExactMatch
from app.engine.structure_analyzer import DocumentStructureAnalyzer
from app.engine.exclusion_engine import ExclusionEngine
from app.engine.citation_engine import CitationEngine
from app.engine.rarity_analyzer import RarityAnalyzer
from app.engine.confidence_model import ConfidenceModel
from app.engine.source_attribution import SourceAttributionEngine
from app.engine.scorer import HybridScorer
from app.engine.highlight_engine import HighlightEngine
from app.engine.config import SimilarityConfig, default_config


class TestPlagXSimilarityEngineV2Benchmark(unittest.TestCase):

    def setUp(self):
        self.config = SimilarityConfig()
        self.exact_engine = ExactMatchEngine(config=self.config.exact_match)
        self.structure_analyzer = DocumentStructureAnalyzer(config=self.config.structure)
        self.exclusion_engine = ExclusionEngine(config=self.config.exclusion, structure_analyzer=self.structure_analyzer)
        self.citation_engine = CitationEngine(config=self.config.citation)
        self.rarity_analyzer = RarityAnalyzer(config=self.config.rarity)
        self.confidence_model = ConfidenceModel(config=self.config.confidence)
        self.source_attribution = SourceAttributionEngine(config=self.config.source_attribution)
        self.scorer = HybridScorer(config=self.config.scoring)
        self.highlight_engine = HighlightEngine(config=self.config.highlight)

    def test_1_identical_document_exact_match(self):
        """Test identical document returns 100% exact similarity score."""
        words = "Artificial intelligence and natural language processing drive modern plagiarism detection systems.".split()
        matches = self.exact_engine.find_matches(words, words, source_id="src1", source_name="Identical Doc")
        score = self.exact_engine.calculate_exact_score(matches, len(words))
        self.assertEqual(score, 100.0)

    def test_2_original_document_low_similarity(self):
        """Test completely original document returns 0% match score."""
        words1 = "The solar energy system operates efficiently under direct sunlight conditions.".split()
        words2 = "Deep neural networks require substantial GPU computation for training.".split()
        matches = self.exact_engine.find_matches(words1, words2, source_id="src2", source_name="Diff Doc")
        score = self.exact_engine.calculate_exact_score(matches, len(words1))
        self.assertEqual(score, 0.0)

    def test_3_bibliography_exclusion(self):
        """Test bibliography and references section is excluded from scoring."""
        text = "Main thesis content.\nReferences\n[1] Author, A. 2025. Title."
        sections = self.structure_analyzer.analyze(text)
        ref_sec = next(s for s in sections if s.section_type == "references")
        self.assertEqual(ref_sec.policy, "exclude")

    def test_4_properly_quoted_citation_adjustment(self):
        """Test properly quoted citations carry minimal weight modifier."""
        text = 'As stated in prior research, "Deep learning models require training data" [1].'
        start = text.find('"Deep') + 1
        end = text.find('data"') + len('data')
        res = self.citation_engine.analyze_span(text, start, end, is_exact=True)
        self.assertEqual(res.citation_status, "Properly Quoted")
        self.assertEqual(res.weight_modifier, self.config.citation.quoted_weight)

    def test_5_common_academic_transition_suppression(self):
        """Test common academic phrases receive low rarity scores."""
        phrase = "In this paper we present an experimental evaluation."
        rarity = self.rarity_analyzer.compute_phrase_rarity(phrase)
        self.assertLessEqual(rarity, 0.3)

    def test_6_rare_technical_phrase_boost(self):
        """Test rare technical terms receive boosted rarity scores."""
        phrase = "Convolutional backpropagation vector quantization"
        rarity = self.rarity_analyzer.compute_phrase_rarity(phrase)
        self.assertGreaterEqual(rarity, 1.0)

    def test_7_multi_source_unique_attribution(self):
        """Test multi-source overlap is attributed uniquely without percentage inflation."""
        span1 = type('Span', (), {'top_source_id': 's1', 'start_char': 0, 'end_char': 50, 'start_word': 0, 'end_word': 10})()
        span2 = type('Span', (), {'top_source_id': 's2', 'start_char': 25, 'end_char': 75, 'start_word': 5, 'end_word': 15})()

        attributions = self.source_attribution.compute_unique_attributions(
            [span1, span2], total_tokens=20, source_names_map={'s1': 'Source 1', 's2': 'Source 2'}
        )
        total_attrib_pct = sum(a.unique_percentage for a in attributions)
        self.assertLessEqual(total_attrib_pct, 100.0)

    def test_8_highlight_boundary_trimming(self):
        """Test highlighting trims leading and trailing punctuation."""
        span = type('Span', (), {'start_char': 0, 'end_char': 15, 'matched_text': '', 'original_text': ''})()
        full_text = "...Hello World!.."
        refined = self.highlight_engine.refine_spans([span], full_text)
        self.assertEqual(refined[0].matched_text, "Hello World")


if __name__ == '__main__':
    unittest.main()
