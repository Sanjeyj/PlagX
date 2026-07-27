"""
Unit Tests for Phase 3 ExclusionEngine
"""

import unittest
from app.engine.exclusion_engine import ExclusionEngine
from app.engine.offset_mapper import DocumentMap, TokenMapping


class TestExclusionEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ExclusionEngine()

    def test_boilerplate_exclusion(self):
        text = "All rights reserved. Submitted in partial fulfillment of the requirements for the degree of Doctor of Philosophy."
        self.assertTrue(self.engine.is_boilerplate(text))

    def test_process_document_token_exclusion(self):
        full_text = "Main content.\nReferences\n[1] Author 2025."
        tokens = [
            TokenMapping("Main", "Main", 0, 4, 0, 0, 0, 1),
            TokenMapping("content", "content", 5, 12, 1, 0, 0, 1),
            TokenMapping("Author", "Author", 28, 34, 2, 1, 1, 1),
        ]
        doc_map = DocumentMap(source_filename="test.txt", full_text=full_text, tokens=tokens)
        
        sections = self.engine.process_document(doc_map)
        # Token at offset 28 falls in References section -> should be marked excluded
        ref_token = doc_map.tokens[2]
        self.assertTrue(ref_token.is_excluded)


if __name__ == '__main__':
    unittest.main()
