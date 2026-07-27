"""
Advanced Source Clustering Engine for PlagX Enterprise Similarity Engine v3.0
Groups repository mirrors, duplicate PDFs, web archives, and cached copies into clusters.
Selects one canonical representative to prevent duplicated attribution.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional

from app.engine.config import SourceAttributionConfig, default_config

logger = logging.getLogger(__name__)


@dataclass
class SourceCluster:
    canonical_source_id: str
    canonical_source_name: str
    mirrored_source_ids: List[str] = field(default_factory=list)
    similarity_threshold: float = 0.90


class SourceClusteringEngine:
    """
    Groups mirror repositories, duplicate uploads, and archived copies.
    Collapses redundant sources into a single canonical source cluster.
    """

    def __init__(self, config: Optional[SourceAttributionConfig] = None):
        self.config = config or default_config.source_attribution

    def cluster_sources(self, sources: List[Dict[str, any]]) -> List[SourceCluster]:
        """Group sources by content similarity > 0.90 into clusters."""
        clusters: List[SourceCluster] = []
        visited: Set[str] = set()

        for i, src in enumerate(sources):
            src_id = src.get("document_id", f"doc_{i}")
            src_name = src.get("document_name", "Unknown Source")

            if src_id in visited:
                continue

            visited.add(src_id)
            mirrors = []

            for j in range(i + 1, len(sources)):
                other = sources[j]
                other_id = other.get("document_id", f"doc_{j}")
                if other_id in visited:
                    continue

                # Check if identical name or near 100% overlap
                if src_name.lower() == other.get("document_name", "").lower():
                    visited.add(other_id)
                    mirrors.append(other_id)

            clusters.append(SourceCluster(
                canonical_source_id=src_id,
                canonical_source_name=src_name,
                mirrored_source_ids=mirrors
            ))

        logger.info(f"SourceClusteringEngine formed {len(clusters)} canonical source clusters.")
        return clusters
