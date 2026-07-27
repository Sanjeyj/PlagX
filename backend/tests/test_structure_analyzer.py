"""
Unit Tests for Phase 2 DocumentStructureAnalyzer
"""

import unittest
from app.engine.structure_analyzer import DocumentStructureAnalyzer, DocumentSection


class TestDocumentStructureAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = DocumentStructureAnalyzer()

    def test_section_detection(self):
        doc_text = """Abstract: This paper presents an AI system.

1. Introduction
Plagiarism detection is critical for academic integrity.

References
[1] Author, A. (2025). Paper title.
"""
        sections = self.analyzer.analyze(doc_text)
        self.assertTrue(any(s.section_type == "abstract" for s in sections))
        self.assertTrue(any(s.section_type == "introduction" for s in sections))
        self.assertTrue(any(s.section_type == "references" for s in sections))

        ref_section = next(s for s in sections if s.section_type == "references")
        self.assertEqual(ref_section.policy, "exclude")
        self.assertEqual(ref_section.weight_modifier, 0.0)


if __name__ == '__main__':
    unittest.main()
