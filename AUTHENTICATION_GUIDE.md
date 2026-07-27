# PlagX Authentication Guide

**Version**: 1.0.0  

---

## 🔑 Authentication Architecture

PlagX implements a stateless JWT (JSON Web Token) authentication architecture paired with direct `bcrypt` password hashing.

### Flow Summary:
1. **User Registration** (`POST /api/auth/register`):
   - Accepts `email`, `full_name`, and `password`.
   - Hashes password using standard `bcrypt.hashpw` with 12 rounds of salt.
   - Stores user record in database.
   - Returns `access_token` (JWT, 30 min expiration), `refresh_token` (JWT, 7 days), and `user` object.

2. **User Login** (`POST /api/auth/login`):
   - Accepts `email` and `password`.
   - Verifies credentials using direct `bcrypt.checkpw`.
   - Returns signed JWT tokens and `user` object.

3. **Protected Endpoint Authorization** (`GET /api/auth/me`):
   - Requires `Authorization: Bearer <access_token>` header.
   - Validates JWT signature, expiration (`exp`), and claims (`sub`).
   - Retrieves active user profile.
