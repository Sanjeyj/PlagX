# PlagX Enterprise Changelog

All notable changes to the PlagX Enterprise similarity engine and platform will be documented in this file.

---

## [5.0.0] - 2026-07-27

### Added
- Enterprise Observability Suite (`/health`, `/readiness`, `/liveness`, `/metrics`) in [main.py](file:///d:/EthicBids%20Technologies/PlagX/backend/app/main.py).
- `X-Correlation-ID` header tracing middleware.
- Full text reconstruction in exact match merging ([exact_match.py](file:///d:/EthicBids%20Technologies/PlagX/backend/app/engine/exact_match.py)).
- Direct `bcrypt` password hashing and verification in [auth_service.py](file:///d:/EthicBids%20Technologies/PlagX/backend/app/services/auth_service.py).
- Unified single URL configuration (`http://localhost:3000`) proxied to backend endpoints ([next.config.ts](file:///d:/EthicBids%20Technologies/PlagX/frontend/next.config.ts)).
- Privacy & Compliance documentation package ([PRIVACY_GUIDE.md](file:///d:/EthicBids%20Technologies/PlagX/PRIVACY_GUIDE.md), [COMPLIANCE_REPORT.md](file:///d:/EthicBids%20Technologies/PlagX/COMPLIANCE_REPORT.md), [DATA_RETENTION_POLICY.md](file:///d:/EthicBids%20Technologies/PlagX/DATA_RETENTION_POLICY.md)).
- End-to-end authentication integration test suite ([test_auth_integration.py](file:///d:/EthicBids%20Technologies/PlagX/backend/tests/test_auth_integration.py)).

### Fixed
- Fixed non-linear score compression bug in `scorer.py`.
- Fixed Axios interceptor refresh loop on `/login` in `api.ts`.
- Resolved `passlib` `bcrypt` attribute error on Python 3.12/3.13.

---

## [3.0.0] - 2026-07-25
- Initial production hardened v3.0 similarity engine pipeline with hybrid BM25 + FAISS search intelligence.
