# PlagX Enterprise Similarity Engine v3.0 — Configuration Reference

This document describes all configurable parameters in `SimilarityConfig` (`backend/app/engine/config.py`).

---

## 1. Exact Match Configuration (`ExactMatchConfig`)

| Parameter | Type | Default | Allowed Range | Description & Impact |
| :--- | :--- | :--- | :--- | :--- |
| `min_ngram` | `int` | `5` | `3` – `10` | Minimum consecutive words to seed an exact n-gram hash match. |
| `min_match_words` | `int` | `5` | `3` – `15` | Minimum total words required for a finalized exact match span. |
| `merge_gap` | `int` | `1` | `0` – `5` | Word gap allowed between adjacent exact matches when merging. |
| `whitelist_filter` | `bool` | `True` | `True/False` | Filter out common academic phrases (e.g. "in accordance with"). |

---

## 2. Semantic Configuration (`SemanticConfig`)

| Parameter | Type | Default | Allowed Range | Description & Impact |
| :--- | :--- | :--- | :--- | :--- |
| `embedding_model` | `str` | `sentence-transformers/all-MiniLM-L6-v2` | PyTorch transformer string | Vector embedding model name. |
| `top_k` | `int` | `3` | `1` – `10` | Top nearest neighbor search count in FAISS index. |
| `high_threshold` | `float` | `0.85` | `0.80` – `0.95` | Cosine similarity threshold for high-confidence semantic matches. |
| `med_threshold` | `float` | `0.75` | `0.70` – `0.85` | Threshold for medium-confidence semantic matches. |
| `low_threshold` | `float` | `0.65` | `0.55` – `0.75` | Threshold for weak/borderline semantic matches. |
| `min_words` | `int` | `6` | `4` – `15` | Minimum words required for a semantic match span. |

---

## 3. Citation Configuration (`CitationConfig`)

| Parameter | Type | Default | Allowed Range | Description & Impact |
| :--- | :--- | :--- | :--- | :--- |
| `quoted_weight` | `float` | `0.05` | `0.0` – `0.2` | Weight modifier for properly quoted and cited spans. |
| `properly_cited_weight` | `float` | `0.10` | `0.0` – `0.3` | Weight modifier for cited but unquoted text. |
| `missing_quotation_weight` | `float` | `0.80` | `0.5` – `1.0` | Weight modifier for exact matches missing quotes. |
| `missing_citation_weight` | `float` | `0.60` | `0.4` – `0.9` | Weight modifier for quoted text missing inline citation. |
| `uncited_copy_weight` | `float` | `1.00` | `0.8` – `1.0` | Weight modifier for uncited verbatim text (maximum penalty). |

---

## 4. Document Structure Configuration (`DocumentStructureConfig`)

| Parameter | Type | Default | Allowed Range | Description & Impact |
| :--- | :--- | :--- | :--- | :--- |
| `bibliography_detection` | `bool` | `True` | `True/False` | Automatically detect and exclude Bibliography/References. |
| `metadata_detection` | `bool` | `True` | `True/False` | Suppress author names, emails, and affiliations. |
| `header_footer_detection` | `bool` | `True` | `True/False` | Exclude running page headers and footers. |

---

## 5. Rarity Configuration (`RarityConfig`)

| Parameter | Type | Default | Allowed Range | Description & Impact |
| :--- | :--- | :--- | :--- | :--- |
| `enabled` | `bool` | `True` | `True/False` | Enable TF-IDF phrase rarity weighting. |
| `common_phrase_penalty` | `float` | `0.2` | `0.1` – `0.4` | Weight multiplier for common academic transitions. |
| `rare_phrase_boost` | `float` | `1.2` | `1.0` – `1.5` | Weight multiplier for rare technical terminology. |

---

## 6. Scoring Configuration (`ScoringConfig`)

| Parameter | Type | Default | Allowed Range | Description & Impact |
| :--- | :--- | :--- | :--- | :--- |
| `engine_version` | `str` | `3.0.0` | SemVer string | Engine version stamp embedded in reports. |
| `scoring_version` | `str` | `3.0.0` | SemVer string | Scoring model version stamp embedded in reports. |
