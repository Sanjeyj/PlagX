# PlagX Privacy & Data Protection Guide — v5.0

**Version**: 5.0.0  
**Effective Date**: 2026-07-27  

---

## 🔒 Privacy & Data Protection Architecture

PlagX Enterprise v5.0 enforces privacy-by-design principles:

1. **Encryption Standards**:
   - **Data in Transit**: TLS 1.3 / HTTPS for all REST APIs and web interfaces.
   - **Data at Rest**: AES-256 encryption for documents and SQLite/PostgreSQL storage.

2. **Temporary File Management**:
   - Uploaded PDF/DOCX files processed in `backend/uploads/` are cleaned up automatically post-analysis.
   - Isolated scratch directories for worker sub-processes.

3. **User Data Consent & Ownership**:
   - Uploaded documents belong exclusively to the submitting user or institution.
   - Vector database indexing (`vector_db/`) uses hashed document tokens without storing raw unhashed text.
