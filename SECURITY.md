# Security Rules

## Secrets

- All keys in .env only; never hardcode
- Never log request bodies containing user data
- .env.example must stay updated with key names (no values)

Required secrets: `SECRET_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ONET_API_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`

## Authentication

- JWT access token: 15min expiry
- JWT refresh token: 7 days, httpOnly cookie
- All /api/ endpoints require authentication except /api/v1/auth/

## Django Hardening

- DEBUG=False in production .env
- ALLOWED_HOSTS must be explicit (no wildcard)
- Use Django's CSRF protection; do not disable it
- CORS: whitelist frontend URL only, not \*

## User Data

- Never store raw military text longer than needed for translation
- No PII logging
- Resume data scoped to authenticated user only (filter by request.user)
- Raw PDF bytes never stored — extracted text only
- chat_history stored in DB server-side — frontend request body history is always ignored to prevent injection
- User.tier field is read-only in the API (UserSerializer) — tier changes only via Django admin

## Input Validation

- job_description: 10–15000 chars enforced in ResumeDraftView (view-level + serializer)
- chat message: max 2,000 chars enforced in ResumeChatView
- Finalize payload: civilian_title (200), summary (3,000), roles (20 max), each role title/org (200), dates (100), bullets (10 max, each 500 chars)
- Contact fields: name/company/role (200), email (254), notes (5,000)

## Rate Limiting

- Login: 5/min (LoginRateThrottle) + Nginx zone (10r/s, burst 10)
- Register: 5/hour (RegisterThrottle)
- Upload/Draft/Chat/Finalize/ONET: tiered (free/pro) via TieredThrottle

## Error Message Normalization (anti-enumeration)

- Login always returns `{"error": "Invalid email or password."}` regardless of failure reason
- Register always returns `{"error": "Registration failed."}` on any validation error

## AI Output Sanitization

- All Claude-generated string fields (civilian_title, summary, roles, bullets) are run through strip_tags() before storage to prevent stored XSS

## File Uploads

- Validate PDF MIME type server-side before passing to PyMuPDF — never trust file extension alone
- Max upload size: 10MB enforced by Nginx client_max_body_size
- Reject any file that does not extract to a non-empty string

## Docker

- Never expose DB port externally in docker-compose.yml
- Backend not directly exposed; all traffic through Nginx

## AWS EC2

- No credentials in any file; use IAM instance role
- Security group: port 80/443 only, no 8000 or 5432 exposed

## HTTPS / SSL

- SSL terminated at Nginx — Django sees `X-Forwarded-Proto: https` via `SECURE_PROXY_SSL_HEADER`
- Certbot (Let's Encrypt) runs on EC2 host, not in Docker
- Cert path: `/etc/letsencrypt/live/cjoewono.com/`
- HSTS enabled in production (31536000 seconds) — do not enable until SSL cert is confirmed working
- HTTP → HTTPS redirect at both Nginx level and Django level (`SECURE_SSL_REDIRECT`)
- `CSRF_TRUSTED_ORIGINS` must include `https://cjoewono.com` in production `.env`
- Auto-renewal: `sudo certbot renew --quiet` via cron (every 12 hours)

## Billing (Stripe)

- PCI-DSS scope: SAQ A — all card data is entered on Stripe-hosted Checkout; the frontend never sees PAN/CVV
- `stripe_customer_id` is the only Stripe reference stored; no payment methods are persisted
- Webhook handler verifies every payload with `stripe.Webhook.construct_event` — unsigned requests are rejected with 400
- Webhook processing is idempotent: duplicate `stripe_event_id` values short-circuit before any DB writes
- Subscription state transitions write to `SubscriptionAuditLog` (immutable in Django admin) for regulatory audit trail
- Idempotency keys included on Stripe Customer and Session creation to prevent double-charges on retry
- Checkout endpoint is rate-limited (5/min) to defeat card-testing/botting
