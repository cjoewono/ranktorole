# Skill: Authentication

Load this file when working on: user registration, login, logout,
JWT tokens, Google OAuth, or any protected endpoint.

## Token Strategy
- Access token: 15 min expiry, sent in Authorization header
- Refresh token: 7 days expiry, stored in httpOnly cookie
- Library: djangorestframework-simplejwt
- All /api/v1/ endpoints require JWT except /api/v1/auth/

## Endpoints
POST /api/v1/auth/register/     → create user, return tokens
POST /api/v1/auth/login/        → validate credentials, return tokens
POST /api/v1/auth/refresh/      → rotate access token
POST /api/v1/auth/logout/       → blacklist refresh token
GET  /api/v1/auth/google/       → OAuth redirect
POST /api/v1/auth/google/callback/ → exchange code, return tokens

## Google OAuth
- Library: social-auth-app-django
- Env vars: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
- Satisfies: "server-side API with OAuth secret key" requirement
- Flow: frontend redirect → Google → callback → JWT issued
- Never expose GOOGLE_CLIENT_SECRET to frontend

## User Model
- Location: user_app/models.py
- Extends: AbstractUser
- Primary key: UUIDv4
- Extra fields: created_at (auto), updated_at (auto)
- No storing of plain passwords — Django handles hashing

## Security Rules
- Validate email format server-side, not just frontend
- Rate limit login endpoint (use django-ratelimit or DRF throttling)
- Blacklist refresh tokens on logout (SimpleJWT blacklist app)
- CORS: whitelist frontend URL only — never wildcard
- CSRF: enabled for all non-JWT endpoints
- Never return password hash in any serializer response
- Log failed login attempts (no PII in logs — email only)

## Frontend Auth Pattern (from BridgeBoard)
- Token stored in localStorage (known tradeoff — acceptable for MVP)
- Passed via Outlet context to all child routes
- All protected routes redirect to /login if no token
- Logout clears localStorage and calls /api/v1/auth/logout/

## Testing
- Test register: valid, duplicate email, missing fields
- Test login: valid, wrong password, nonexistent user
- Test refresh: valid token, expired token, blacklisted token
- Test protected endpoint: with token, without token, expired token