# Security Rules

## Secrets

- All keys in `.env` only; never hardcode
- Never log request bodies containing user data
- `.env.example` must stay updated with key names (no values)

Required secrets: `SECRET_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, `ONET_API_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, `STRIPE_CHECKOUT_SUCCESS_URL`, `STRIPE_CHECKOUT_CANCEL_URL`.

`SECRET_KEY` must be ≥32 bytes (RFC 7518). Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.

## Authentication

- JWT access token: 15min expiry, stored in frontend memory only
- JWT refresh token: 7 days, httpOnly cookie with rotation + blacklisting
- All `/api/` endpoints require authentication except `/api/v1/auth/` and `/api/v1/billing/webhook/`

## Django Hardening

- `DEBUG=False` in production `.env`
- `ALLOWED_HOSTS` must be explicit (no wildcard)
- Use Django's CSRF protection; do not disable it (one exception: Stripe webhook endpoint, because Stripe signs the request body)
- CORS: whitelist frontend URL only, not `*`

## User Data

- Never store raw military text longer than needed for translation
- No PII logging
- Resume data scoped to authenticated user only (filter by `request.user`)
- Raw PDF bytes never stored — extracted text only
- `chat_history` stored in DB server-side — frontend request body history is always ignored to prevent injection
- `User.tier` and `User.subscription_status` are read-only in the API (`UserSerializer`) — tier changes only via the Stripe webhook

## Input Validation

- `job_description`: 10–15,000 chars enforced in `ResumeDraftView` (view-level + serializer)
- Chat `message`: max 2,000 chars enforced in `ResumeChatView`
- Finalize payload: `civilian_title` (200), `summary` (3,000), `roles` (20 max), each role `title`/`org` (200), `dates` (100), `bullets` (10 max, each 500 chars)
- Contact fields: `name`/`company`/`role` (200), `email` (254, RFC 5321), `notes` (5,000)

## Rate Limiting

- Login: 5/min (`LoginRateThrottle`) + Nginx zone (10r/s, burst 10)
- Register: 5/hour (`RegisterThrottle`, anti-enumeration)
- Upload/Draft/Chat/Finalize/ONET: tiered (free/pro) via `TieredThrottle` subclasses
- Billing checkout/portal: 5/min (`CheckoutThrottle`, anti card-testing)

## Tier Enforcement (DRF Permissions)

Two permission classes in `user_app/permissions.py` gate free-tier usage in
addition to rate limits:

- `IsProOrUnderLimit` — daily-resetting per-user counter (`resume_tailor_count`). Pro users (`subscription_status ∈ {active, trialing, past_due}` and `tier == 'pro'`) bypass.
- `ChatTurnLimit` — permanent per-resume counter (`Resume.chat_turn_count`) against `settings.FREE_TIER_CHAT_LIMIT`. Pro users bypass.

Lazy daily reset: `_reset_if_new_day()` zeroes counters on first hit after UTC midnight. No cron required.

## Error Message Normalization (anti-enumeration)

- Login always returns `{"error": "Invalid email or password."}` regardless of failure reason
- Register always returns `{"error": "Registration failed."}` on any validation error

## AI Output Sanitization

- All Claude-generated string fields (`civilian_title`, `summary`, `roles`, `bullets`) are run through `strip_tags()` before storage to prevent stored XSS

## File Uploads

- Validate PDF MIME type server-side before passing to PyMuPDF — never trust file extension alone
- Validate `%PDF-` magic bytes — prevents spoofed MIME types
- Max upload size: 10MB (enforced both in view and by Nginx `client_max_body_size`)
- Reject any file that does not extract to a non-empty string

## Docker

- Never expose DB port externally in `docker-compose.yml`
- Backend not directly exposed; all traffic through Nginx
- No secrets baked into Docker images — all via `.env` at runtime

## AWS EC2

- No credentials in any file; use IAM instance role
- Security group: ports 80/443 open to world; 22 from admin IP only; no 8000 or 5432 exposed

## HTTPS / SSL

- SSL terminated at Nginx — Django sees `X-Forwarded-Proto: https` via `SECURE_PROXY_SSL_HEADER`
- Certbot (Let's Encrypt) runs on EC2 host, not in Docker
- Cert path: `/etc/letsencrypt/live/cjoewono.com/`
- HSTS enabled in production (31,536,000 seconds / 1 year) — do not enable until SSL cert is confirmed working
- HTTP → HTTPS redirect at both Nginx level and Django level (`SECURE_SSL_REDIRECT`)
- `CSRF_TRUSTED_ORIGINS` must include `https://cjoewono.com` in production `.env`
- Auto-renewal: `sudo certbot renew --quiet` via cron (every 12 hours)

## Billing (Stripe)

- PCI-DSS scope: SAQ A — all card data is entered on Stripe-hosted Checkout; the frontend never sees PAN/CVV
- `stripe_customer_id` is the only Stripe reference stored; no payment methods are persisted
- Webhook handler verifies every payload with `stripe.Webhook.construct_event` **before any DB work** — unsigned requests are rejected with 400
- Webhook processing is idempotent: duplicate `stripe_event_id` values short-circuit before any DB writes
- Subscription state transitions write to `SubscriptionAuditLog` (immutable, append-only) for regulatory audit trail
- Idempotency keys included on Stripe Customer and Session creation to prevent double-charges on retry
- Checkout endpoint is rate-limited (5/min) to defeat card-testing / botting
- `User.tier` is not writable via any API — only the webhook handler can change it

## Dependency Pinning

The following packages are intentionally pinned to older versions pre-deadline.
Do **not** upgrade without explicit go-ahead:

- `social-auth-app-django==5.4.2` — 5.6.0 requires Django 5.1; we are on 4.2 LTS
- `anthropic==0.40.0` — later SDK versions carry breaking changes not worth absorbing pre-deadline
- `Django==4.2.30` — on 4.2 LTS line; next minor upgrades should wait until post-launch

## AI Enrichment (Career Recon)

**Five layers of defense (defense in depth):**

1. **Auth + profile gate** — `IsAuthenticated` permission class. Empty `profile_context` returns 400, not a Haiku call. Both checks run before any external API call.

2. **Per-user tiered throttle** — `ReconEnrichThrottle` enforces 15/day (free) / 25/day (pro) via `TIERED_THROTTLE_RATES`. Cache hits do not consume throttle quota.

3. **DB-backed result cache** — Profile-aware SHA256 cache key means MOS/branch changes get fresh enrichment (correctness), not stale output. Two users with identical profile fields share a cache entry (no PII in enrichment response — output is derived solely from O\*NET public data + profile tier/branch/mos/skills). 7-day TTL.

4. **Hard API timeout** — `RECON_ENRICH_TIMEOUT_SECONDS = 15.0` prevents backend thread pile-up on Anthropic partial outages. Haiku P95 is ~3s; 15s is a generous backstop.

5. **Global daily ceiling** — `RECON_ENRICH_DAILY_CEILING` (default 500, env-configurable). Ceiling is enforced with incr-first atomic pattern to prevent TOCTOU over-count across gunicorn workers.

**XSS defense** — All Haiku string outputs sanitized with `strip_tags` before caching and before returning to client.

**Prompt injection hardening** — `profile_context` fields (branch/mos/skills) go into the Haiku prompt. Malicious prompt injection via The Forge profile is a recognized attack surface; field values are length-capped in the prompt builder. Schema-level `max_length` constraints on `CareerEnrichment` reject runaway LLM responses.

**No bullet fabrication** — Haiku prompt explicitly instructs: "DO NOT generate resume bullets, XYZ-format accomplishments, or fabricated metrics." Enforced by schema design (no bullets field) and explicit prompt instruction.

**O\*NET data trust** — O\*NET career data is fetched server-side; client never passes career payload. Profile context is read from `request.user`, never from request body.

### MOS Title Grounding

Enrichment prompts always include a validated military title (or explicit
"not verified" sentinel). This prevents Haiku from fabricating military job
duties when given only a numeric code. Titles come from:

1. Local dicts (`NAVY_OFFICER_DESIGNATORS`, `COAST_GUARD_RATINGS`) for branches
   where O\*NET has no coverage
2. O\*NET `/veterans/military/` endpoint for all other branches
3. Prefix-match fallback for AF/USSF hierarchical codes

Resolved titles cached 30 days per `(branch, mos)` key. On miss, the prompt
explicitly instructs Haiku to speak at branch level only and not invent
specifics. This is a trust-critical control — veterans detect fabricated
military titles immediately and lose product confidence.
