"""
Unit Tests for Phase 4 SourceClusteringEngine
"""

import unittest
from app.engine.source_clustering import SourceClusteringEngine


class TestSourceClusteringEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SourceClusteringEngine()

    def test_mirror_clustering(self):
        sources = [
            {"document_id": "doc1", "document_name": "Thesis_Draft.pdf"},
            {"document_id": "doc2", "document_name": "Thesis_Draft.pdf"},
            {"document_id": "doc3", "document_name": "Different_Paper.pdf"},
        ]
        clusters = self.engine.cluster_sources(sources)
        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0].canonical_source_id, "doc1")
        self.assertIn("doc2", clusters[0].mirrored_source_ids)


if __name__ == '__main__':
    unittest.main()
