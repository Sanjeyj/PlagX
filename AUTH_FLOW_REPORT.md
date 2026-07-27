# PlagX Authentication Audit & Root Cause Report

**Audit Date**: 2026-07-27  

---

## 🔍 Root Cause Analysis

### Identified Issue 1: Frontend Interceptor Refresh Loop
- **Symptom**: Clicking "Sign in" on `/login` or registering resulted in an immediate silent browser page reload without displaying error messages or signing in.
- **Root Cause**: In `frontend/src/lib/api.ts`, the Axios response interceptor intercepted any `401 Unauthorized` status and executed `window.location.href = '/login'`. Because the browser was already on `/login`, this forced a full page reload, wiping React state before `handleLogin` could render the error toast or process the token.
- **Resolution**: Updated `api.ts` so `401` response interceptor ignores `/auth/login` and `/auth/register` routes and suppresses page reloads when already on `/login` or `/signup`.

### Identified Issue 2: Passlib / Bcrypt Attribute Error
- **Symptom**: `AttributeError: module 'bcrypt' has no attribute '__about__'` thrown inside `passlib.handlers.bcrypt`.
- **Root Cause**: `passlib` is unmaintained and incompatible with `bcrypt >= 4.0.0`.
- **Resolution**: Replaced `passlib.context.CryptContext` in `backend/app/services/auth_service.py` with direct `bcrypt.hashpw` and `bcrypt.checkpw` functions.

---

## 🧪 Verification Results
- 100% of authentication unit, integration, and lifecycle tests (`test_auth_integration.py`) passed cleanly.
