# PlagX Enterprise AI/ML Model Catalog — v5.0

---

## 🤖 Deployed Machine Learning Models

### 1. Sentence-Transformers Vector Embedding Model
- **Model Name**: `sentence-transformers/all-MiniLM-L6-v2`
- **Purpose**: Generates dense 384-dimensional vector embeddings for sentence and paragraph similarity.
- **Training Data**: 1B+ sentence pairs (SNLI, MultiNLI, MS MARCO, Wikipedia).
- **Fallback Behavior**: Lexical BM25 overlap matching if vector inference is disabled.

### 2. spaCy Natural Language Processing Pipeline
- **Model Name**: `en_core_web_sm`
- **Purpose**: Sentence segmentation, tokenization, and lemmatization.
- **Fallback Behavior**: Regex-based tokenization and whitespace splitting.

### 3. RoBERTa AI Detector
- **Model Name**: `roberta-base-openai-detector`
- **Purpose**: Evaluates text perplexity and burstiness to estimate AI-generated content probability.
- **Fallback Behavior**: Stylometric heuristic check.
