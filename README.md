# PlagX — AI Plagiarism Detection Platform

Enterprise-grade plagiarism detection system powered by semantic AI. Similar to Turnitin but built entirely from scratch with modern open-source technologies.

## Features

- **Multi-format Support**: Upload PDF, DOCX, TXT files
- **Exact Match Detection**: N-gram hashing with Rabin-Karp matching
- **Semantic Analysis**: sentence-transformers/all-MiniLM-L6-v2
- **FAISS Vector Search**: Ultra-fast similarity retrieval
- **Citation Exclusion**: Automatically exclude bibliography & citations
- **Highlight Injection**: Precise inline highlighting with source attribution
- **PDF Reports**: Playwright-rendered professional reports
- **Dashboard**: Stats, document management, report history
- **JWT Authentication**: Secure user accounts

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS, ShadCN UI |
| Backend | FastAPI, SQLAlchemy, PostgreSQL |
| AI/NLP | sentence-transformers, FAISS, spaCy |
| Queue | Celery + Redis |
| Reports | Jinja2 + Playwright PDF |
| Deploy | Docker Compose |

## Quick Start (Docker)

```bash
# Clone and start all services
docker-compose up -d

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Local Development

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
playwright install chromium

# Start PostgreSQL and Redis (or use Docker)
docker run -d --name pg -e POSTGRES_DB=plagx -e POSTGRES_USER=plagx -e POSTGRES_PASSWORD=plagx_secret -p 5432:5432 postgres:15-alpine
docker run -d --name redis -p 6379:6379 redis:7-alpine

uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register user |
| POST | /api/auth/login | Login |
| GET | /api/auth/me | Current user |
| POST | /api/upload | Upload document |
| POST | /api/check/{id} | Start plagiarism check |
| GET | /api/check-status/{id} | Check progress |
| GET | /api/documents | List documents |
| GET | /api/report/{id} | Get report data |
| GET | /api/report/{id}/pdf | Download PDF |
| GET | /api/dashboard/stats | Dashboard statistics |

## Architecture

```
PlagX/
├── frontend/          # Next.js 16 + TypeScript + ShadCN
├── backend/
│   ├── app/
│   │   ├── api/       # FastAPI routes
│   │   ├── engine/    # Plagiarism detection core
│   │   │   ├── extractor.py       # PDF/DOCX/TXT extraction
│   │   │   ├── offset_mapper.py   # Character offset tracking
│   │   │   ├── preprocessor.py    # Text normalization
│   │   │   ├── chunker.py         # Sentence-aware chunking
│   │   │   ├── citation_excluder.py # Bibliography exclusion
│   │   │   ├── exact_match.py     # N-gram matching
│   │   │   ├── semantic.py        # Embedding similarity
│   │   │   ├── vector_store.py    # FAISS index
│   │   │   ├── scorer.py          # Hybrid scoring
│   │   │   └── pipeline.py        # Orchestrator
│   │   ├── models/    # SQLAlchemy ORM
│   │   ├── report/    # HTML/PDF generation
│   │   ├── schemas/   # Pydantic validation
│   │   ├── services/  # Business logic
│   │   └── tasks/     # Celery workers
│   └── requirements.txt
├── docker/            # Dockerfiles
└── docker-compose.yml
```

## Scoring Formula

```
Final Score = 40% Exact Match + 40% Semantic Similarity + 20% Source Density
```

| Range | Risk Level |
|-------|-----------|
| 0–10% | Low |
| 10–25% | Moderate |
| 25–50% | Suspicious |
| 50%+ | High Risk |
