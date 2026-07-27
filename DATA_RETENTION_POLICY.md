# PlagX Data Retention & Purge Policy — v5.0

**Effective Date**: 2026-07-27  

---

## 🗑️ Data Retention Schedule

| Data Category | Retention Period | Purge Action |
| :--- | :--- | :--- |
| **Uploaded Raw Files** | 24 Hours | Automated filesystem shredding from `./uploads/`. |
| **Analysis PDF Reports** | 30 Days | Retained in `./reports/` unless user requests deletion. |
| **User Activity Logs** | 90 Days | Rotated and archived via structured logging. |
| **FAISS Vector Embeddings** | Indefinite | Retained in corpus store for similarity matching. |
