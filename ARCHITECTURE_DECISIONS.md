# PlagX Architecture Decision Records (ADR) — v3.0

---

## ADR 001: Modular Engine Architecture
- **Decision**: Decouple plagiarism analysis into 13 independent Python modules under `backend/app/engine/`.
- **Rationale**: Isolates exact matching, semantic retrieval, structure parsing, citation classification, and scoring into clean, independently testable units.

## ADR 002: Zero Magic Numbers Configuration
- **Decision**: Externalize 100% of algorithmic parameters into `SimilarityConfig`.
- **Rationale**: Guarantees deterministic, reproducible behavior without hidden hardcoded heuristics.

## ADR 003: Weighted Academic Similarity Model
- **Decision**: Replace raw linear / non-linear ratio with multi-factor weighted scoring:
  $$\text{Similarity} = \text{Unique Suspicious Coverage} \times \text{Confidence} \times \text{Context} \times \text{Rarity} \times \text{Citation Adjustment}$$
- **Rationale**: Accurately reflects academic integrity rules by prioritizing uncited verbatim copies over properly cited quotations and generic formulas.

## ADR 004: $O(N \log N)$ Sweep-Line Interval Union
- **Decision**: Use sweep-line event sorting and token coverage mapping.
- **Rationale**: Completely eliminates duplicate overlap inflation while preserving $O(N \log N)$ computational complexity for large documents.

## ADR 005: Explainability Metadata API
- **Decision**: Attach full diagnostic metadata to every `MatchSpan` and expose `GET /api/report/{id}/explain`.
- **Rationale**: Provides 100% transparency for academic advisors, students, and administrators to understand exactly *why* a region was flagged.
