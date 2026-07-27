# PlagX Enterprise REST API Reference — v5.0

---

## 📡 Base Endpoint Architecture

- **Unified Single Base URL**: `http://localhost:3000/api` (or direct backend `http://127.0.0.1:8000/api`)

---

## 🔐 Authentication Endpoints

### `POST /api/auth/register`
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "full_name": "Dr. Alice Smith",
    "password": "SecurePassword123!"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "user": { "id": "...", "email": "user@example.com", "full_name": "Dr. Alice Smith" }
  }
  ```

### `POST /api/auth/login`
- **Request Body**: `{"email": "user@example.com", "password": "SecurePassword123!"}`
- **Response (200 OK)**: `{"access_token": "...", "refresh_token": "...", "user": {...}}`

### `GET /api/auth/me`
- **Headers**: `Authorization: Bearer <access_token>`
- **Response (200 OK)**: `{"id": "...", "email": "user@example.com", "full_name": "Dr. Alice Smith"}`

---

## 📄 Similarity Analysis & Report Endpoints

### `POST /api/documents/scan`
- **Multipart Form Data**: `file` (`.pdf`, `.docx`, `.txt`)
- **Headers**: `Authorization: Bearer <access_token>`
- **Response (202 Accepted)**: `{"document_id": "...", "task_id": "...", "status": "processing"}`

### `GET /api/report/{report_id}`
- **Response (200 OK)**: Full similarity report JSON.

### `GET /api/report/{report_id}/explain`
- **Response (200 OK)**:
  ```json
  {
    "report_id": "...",
    "overall_similarity": 42.5,
    "scoring_model": "Weighted Academic Similarity Model",
    "explainability_data": [
      {
        "source_name": "Academic Journal Sample",
        "exact_overlap_percent": 35.0,
        "semantic_overlap_percent": 7.5,
        "confidence_score": 0.98,
        "citation_status": "Missing Quotation",
        "evidence": "Contiguous 85-word exact match span"
      }
    ]
  }
  ```

---

## 🩺 System Observability & Health Probes

- `GET /health` — Application status (`{"status": "healthy", "engine_version": "5.0.0"}`)
- `GET /readiness` — Readiness probe (`{"status": "ready"}`)
- `GET /liveness` — Liveness probe (`{"status": "alive"}`)
- `GET /metrics` — Operations & performance metrics
