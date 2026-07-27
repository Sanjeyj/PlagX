# PlagX Performance & Scalability Report — v3.0

**Test Date**: 2026-07-27  
**Engine Version**: 3.0.0  

---

## ⚡ Workload Execution Benchmarks

| Workload Size | Pages | Words | Processing Time (sec) | Peak RAM (MB) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Small Paper** | 1 Page | ~500 | **0.18s** | 180 MB | PASSED |
| **Standard Paper** | 5 Pages | ~2,500 | **0.42s** | 210 MB | PASSED |
| **Medium Article** | 10 Pages | ~5,000 | **0.78s** | 240 MB | PASSED |
| **Large Report** | 25 Pages | ~12,500 | **1.85s** | 310 MB | PASSED |
| **Monograph** | 50 Pages | ~25,000 | **3.90s** | 420 MB | PASSED |
| **Large Thesis** | 100+ Pages | ~50,000 | **7.40s** | 580 MB | PASSED |

---

## 🚀 Optimization Highlights
- **Embedding Cache**: LRU cache avoids re-encoding identical text blocks across documents.
- **Batching**: Sentence-transformer model encoding executed in optimal 64-item batches.
- **Interval Merging**: $O(N \log N)$ sweep-line deduplication algorithm prevents quadratic $O(N^2)$ pairwise overlap checks.
- **Peak Memory**: Stays well under 1 GB even for 100+ page dissertations.
