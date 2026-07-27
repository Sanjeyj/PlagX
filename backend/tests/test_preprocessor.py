"""
Unit Tests for Phase 3 Document Normalization in TextPreprocessor
"""

import unittest
from app.engine.preprocessor import TextPreprocessor


class TestTextPreprocessor(unittest.TestCase):

    def setUp(self):
        self.preprocessor = TextPreprocessor()

    def test_ligature_and_unicode_normalization(self):
        text = "The ﬁrst paper on ﬂuid dynamics."
        normalized = self.preprocessor.normalize_text_elements(text)
        self.assertEqual(normalized, "The first paper on fluid dynamics.")

    def test_ocr_artifact_cleaning(self):
        text = "Deep\u200b learning\ufeff models\u00ad"
        normalized = self.preprocessor.normalize_text_elements(text)
        self.assertEqual(normalized, "Deep learning models")


if __name__ == '__main__':
    unittest.main()
