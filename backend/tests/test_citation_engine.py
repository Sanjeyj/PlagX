"""
Unit Tests for Phase 7 CitationEngine
"""

import unittest
from app.engine.citation_engine import CitationEngine


class TestCitationEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CitationEngine()

    def test_properly_quoted_and_cited(self):
        text = 'As stated in prior research, "Plagiarism detection requires robust NLP pipelines" [1].'
        # Start char of quoted text
        start_char = text.find('"Plagiarism') + 1
        end_char = text.find('pipelines"') + len('pipelines')

        res = self.engine.analyze_span(text, start_char, end_char, is_exact=True)
        self.assertEqual(res.citation_status, "Properly Quoted")
        self.assertEqual(res.weight_modifier, self.engine.config.quoted_weight)

    def test_uncited_copy(self):
        text = 'Plagiarism detection requires robust NLP pipelines without any attribution.'
        res = self.engine.analyze_span(text, 0, len(text), is_exact=True)
        self.assertEqual(res.citation_status, "Uncited Copy")
        self.assertEqual(res.weight_modifier, 1.0)


if __name__ == '__main__':
    unittest.main()
