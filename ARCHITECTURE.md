# PlagX Enterprise System Architecture — v5.0

---

## 🏛️ Architecture Overview

PlagX Enterprise is built on a decoupled, modular architecture adhering strictly to SOLID, DRY, and clean architectural boundaries.

```
┌─────────────────────────────────────────────────────────┐
│              Next.js 16 Web UI (Port 3000)             │
└────────────────────────────┬────────────────────────────┘
                             │  HTTP / REST (proxied /api)
┌────────────────────────────▼────────────────────────────┐
│                FastAPI Backend (Port 8000)              │
├─────────────────────────────────────────────────────────┤
│  • Auth Router (/api/auth)                              │
│  • Documents Router (/api/documents)                    │
│  • Reports Router (/api/report)                         │
│  • Observability (/health, /readiness, /metrics)        │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│             Similarity Engine Pipeline v3.0             │
├─────────────────────────────────────────────────────────┤
│  1. Text Extraction & Offset Mapping                    │
│  2. Document Structure Analyzer                         │
│  3. Exclusion Engine (Bibliography/Metadata/Headers)    │
│  4. Search Intelligence (BM25 + FAISS Hybrid)           │
│  5. Exact Match Engine (N-gram + Rabin-Karp)            │
│  6. Semantic Engine (Sentence Transformers)             │
│  7. Rarity Analyzer (TF-IDF Weighting)                  │
│  8. Citation Engine (Status & Proximity Classification) │
│  9. Confidence Model                                    │
│ 10. Source Attribution & Clustering Engine              │
│ 11. Weighted Academic Similarity Scorer                 │
│ 12. Highlight Engine (Boundary Punctuation Alignment)   │
└─────────────────────────────────────────────────────────┘
```

---

## 🔒 Security & Data Boundaries
- **Authentication**: JWT token stateless authentication with direct `bcrypt` password hashing.
- **Observability**: `X-Correlation-ID` middleware attached to all requests and responses.
- **Privacy**: Temporary upload file cleanup and AES-256 encrypted persistent storage.
