"""
FAISS Vector Store Engine
Manages vector indices for fast semantic similarity search.
Stores chunk embeddings with metadata for source attribution.
"""

import json
import logging
import numpy as np
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VectorMetadata:
    """Metadata associated with a stored vector."""
    vector_id: int
    chunk_id: int
    document_id: str
    document_name: str
    text: str
    original_text: str
    paragraph_index: int
    start_char: int
    end_char: int
    page_number: int


class VectorStore:
    """
    FAISS-based vector store for fast semantic similarity search.
    Stores embeddings with JSON sidecar metadata files.
    """

    def __init__(self, store_dir: str = "./vector_db"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._index = None
        self._metadata: list[VectorMetadata] = []
        self._dimension = 384  # all-MiniLM-L6-v2 dimension

    @property
    def index(self):
        if self._index is None:
            self._init_index()
        return self._index

    def _init_index(self):
        """Initialize a new FAISS index."""
        import faiss
        self._index = faiss.IndexFlatIP(self._dimension)  # Inner product for cosine sim
        logger.info(f"Initialized FAISS index (dim={self._dimension})")

    def add_vectors(
        self,
        embeddings: np.ndarray,
        chunks: list,
        document_id: str,
        document_name: str,
    ):
        """Add chunk embeddings to the index with metadata."""
        if embeddings.size == 0:
            return

        import faiss

        # Normalize for cosine similarity via inner product
        faiss.normalize_L2(embeddings)

        start_id = self.index.ntotal
        self.index.add(embeddings)

        for i, chunk in enumerate(chunks):
            meta = VectorMetadata(
                vector_id=start_id + i,
                chunk_id=chunk.chunk_id,
                document_id=document_id,
                document_name=document_name,
                text=chunk.text,
                original_text=chunk.original_text,
                paragraph_index=chunk.paragraph_index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                page_number=chunk.page_number,
            )
            self._metadata.append(meta)

        logger.info(f"Added {len(chunks)} vectors for {document_name} (total: {self.index.ntotal})")

    def search(
        self,
        query_embeddings: np.ndarray,
        k: int = 5,
        exclude_doc_id: Optional[str] = None,
    ) -> list[list[tuple[VectorMetadata, float]]]:
        """
        Search for nearest neighbors.
        Returns list of results per query, each containing (metadata, similarity) tuples.
        """
        import faiss

        if self.index.ntotal == 0 or query_embeddings.size == 0:
            return [[] for _ in range(len(query_embeddings))]

        # Normalize query embeddings
        query_norm = query_embeddings.copy()
        faiss.normalize_L2(query_norm)

        # Search with extra results to account for exclusions
        search_k = min(k * 3, self.index.ntotal)
        scores, indices = self.index.search(query_norm, search_k)

        results = []
        for q_idx in range(len(query_embeddings)):
            query_results = []
            for j in range(search_k):
                idx = int(indices[q_idx][j])
                score = float(scores[q_idx][j])

                if idx < 0 or idx >= len(self._metadata):
                    continue

                meta = self._metadata[idx]

                # Exclude results from the same document
                if exclude_doc_id and meta.document_id == exclude_doc_id:
                    continue

                query_results.append((meta, score))
                if len(query_results) >= k:
                    break

            results.append(query_results)

        return results

    def save(self, name: str = "default"):
        """Save index and metadata to disk."""
        import faiss

        index_path = self.store_dir / f"{name}.index"
        meta_path = self.store_dir / f"{name}.meta.json"

        faiss.write_index(self.index, str(index_path))

        meta_dicts = [asdict(m) for m in self._metadata]
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_dicts, f, indent=2)

        logger.info(f"Saved index ({self.index.ntotal} vectors) to {index_path}")

    def load(self, name: str = "default") -> bool:
        """Load index and metadata from disk."""
        import faiss

        index_path = self.store_dir / f"{name}.index"
        meta_path = self.store_dir / f"{name}.meta.json"

        if not index_path.exists() or not meta_path.exists():
            logger.info("No existing index found, starting fresh")
            return False

        self._index = faiss.read_index(str(index_path))

        with open(meta_path, "r", encoding="utf-8") as f:
            meta_dicts = json.load(f)
        self._metadata = [VectorMetadata(**m) for m in meta_dicts]

        logger.info(f"Loaded index ({self.index.ntotal} vectors) from {index_path}")
        return True

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal if self._index else 0

    def get_source_documents(self) -> list[dict]:
        """Get list of unique source documents in the store."""
        docs = {}
        for m in self._metadata:
            if m.document_id not in docs:
                docs[m.document_id] = {
                    "document_id": m.document_id,
                    "document_name": m.document_name,
                    "chunk_count": 0,
                }
            docs[m.document_id]["chunk_count"] += 1
        return list(docs.values())
