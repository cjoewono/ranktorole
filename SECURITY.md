# Security Rules

## Secrets
- All keys in .env only; never hardcode
- Never log request bodies containing user data
- .env.example must stay updated with key names (no values)

## Authentication
- JWT access token: 15min expiry
- JWT refresh token: 7 days, httpOnly cookie
- All /api/ endpoints require authentication except /api/v1/auth/

## Django Hardening
- DEBUG=False in production .env
- ALLOWED_HOSTS must be explicit (no wildcard)
- Use Django's CSRF protection; do not disable it
- CORS: whitelist frontend URL only, not *

## User Data
- Never store raw military text longer than needed for translation
- No PII logging
- Resume data scoped to authenticated user only (filter by request.user)

## Docker
- Never expose DB port externally in docker-compose.yml
- Backend not directly exposed; all traffic through Nginx

## AWS EC2
- No credentials in any file; use IAM instance role
- Security group: port 80/443 only, no 8000 or 5432 exposed