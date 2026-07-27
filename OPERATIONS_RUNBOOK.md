# PlagX Enterprise Operations Runbook — v5.0

---

## 🛠️ Operations & Incident Management Procedures

### 1. Service Startup & Verification
```bash
# Start FastAPI backend
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Start Next.js frontend
cd frontend
npm run dev
```

### 2. Observability & Health Verification
```bash
curl http://localhost:3000/health
curl http://localhost:3000/readiness
curl http://localhost:3000/metrics
```

### 3. Automated Test Execution
```bash
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests
```

### 4. Incident Response & Troubleshooting
- **Failed Logins**: Verify `/api/auth/login` returns 401 on bad credentials without triggering full page reload.
- **Engine Performance**: Inspect `PERFORMANCE_REPORT.md` and verify single document scan latency remains under 10 seconds.
