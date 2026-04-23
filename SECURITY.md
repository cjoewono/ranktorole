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
- Upload/Draft/Chat/Finalize/Recon brainstorm: tiered (free/pro) via `TieredThrottle` subclasses
- Billing checkout/portal: 5/min (`CheckoutThrottle`, anti card-testing)

`tiered_throttle_exception_handler` in `translate_app/throttles.py` rewrites the
429 response body to `{code: "DAILY_LIMIT_REACHED", retry_after_seconds: …}` **only**
for tiered user-daily scopes (`user_upload`, `user_draft`, `user_chat`,
`user_finalize`, `user_onet`, `user_recon_brainstorm`). All other throttles —
`AnonRateThrottle`, `LoginRateThrottle`, `RegisterThrottle`, `CheckoutThrottle` —
fall through to DRF's default 429 message so unauthenticated users never see
tier-cap language during normal browsing or auth flows.

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
- Cert path: `/etc/letsencrypt/live/ranktorole.app/`
- HSTS enabled in production (31,536,000 seconds / 1 year) — do not enable until SSL cert is confirmed working
- HTTP → HTTPS redirect at both Nginx level and Django level (`SECURE_SSL_REDIRECT`)
- `CSRF_TRUSTED_ORIGINS` must include `https://ranktorole.app` in production `.env`
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

## Billing & Payment Flows

- PCI scope is SAQ A. The application never sees, stores, or transmits card data. All card entry is on Stripe-hosted Checkout.
- `user.tier` is writable only by `StripeWebhookView`. Frontend observes tier via `GET /api/v1/auth/profile/` and never sets it.
- `PortalSessionView` enforces a `return_url` allowlist: only `https://ranktorole.app/*` and `http://localhost:*` are accepted. All other values return 400.
- `CheckoutSessionView` and `PortalSessionView` are both throttled at 5/min per user (`CheckoutThrottle`) to defeat card-testing and portal-session spamming.
- Post-checkout, `/billing/success` polls `GET /api/v1/auth/profile/` to observe the webhook-driven tier flip. The `session_id` query parameter is displayed for diagnostics only and is never used to authorize a tier change.
- Production security headers (HSTS with preload, SSL redirect, secure cookies, X-Frame-Options DENY) are set in `settings.py` when `DEBUG` is False.

## Dependency Pinning

The following packages are intentionally pinned to older versions pre-deadline.
Do **not** upgrade without explicit go-ahead:

- `social-auth-app-django==5.4.2` — 5.6.0 requires Django 5.1; we are on 4.2 LTS
- `anthropic==0.40.0` — later SDK versions carry breaking changes not worth absorbing pre-deadline
- `Django==4.2.30` — on 4.2 LTS line; next minor upgrades should wait until post-launch

## AI Enrichment (Career Recon)

**Five layers of defense (defense in depth):**

1. **Auth gate** — `IsAuthenticated` permission class. Unauthenticated requests are rejected before any external API call.

2. **Per-user tiered throttle** — `ReconEnrichThrottle` (scope `user_recon_brainstorm`) enforces 15/day (free) / 25/day (pro) via `TIERED_THROTTLE_RATES`. Cache hits do not consume throttle quota.

3. **Profile-independent result cache** — SHA256 of normalized form inputs (not profile). Two users with identical form submissions share a cache entry. 7-day TTL. Profile decoupling removes the risk of stale enrichment on profile edits.

4. **Hard API timeout** — `RECON_ENRICH_TIMEOUT_SECONDS = 15.0` prevents backend thread pile-up on Anthropic partial outages. Haiku P95 is ~3s; 15s is a generous backstop.

5. **Global daily ceiling** — `RECON_ENRICH_DAILY_CEILING` (default 500, env-configurable). Ceiling is enforced with incr-first atomic pattern to prevent TOCTOU over-count across gunicorn workers.

**XSS defense** — All Haiku string outputs sanitized with `strip_tags` before caching and before returning to client.

**Input injection hardening** — Form fields (branch/mos_code/target_career_field) go into the Haiku prompt. Field values are length-capped via `BrainstormInputSerializer` before reaching the prompt builder. `BrainstormRanking` schema-level constraints reject runaway LLM responses.

**No bullet fabrication** — Haiku prompt explicitly instructs against generating resume bullets, XYZ-format accomplishments, or fabricated metrics. Enforced by schema design (no bullets field) and explicit prompt instruction.

**Baseline grounding** — O\*NET crosswalk results form the baseline. Haiku can only pick codes from this list; any code outside the baseline is discarded. Prevents hallucinated O\*NET codes from reaching the response.

**O\*NET data trust** — O\*NET career data is fetched server-side from the form inputs; client never passes career payload. Profile context is never read — form body is the sole input.

### MOS Title Grounding

Brainstorm prompts always include a validated military title (or explicit
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

## Known Accepted Risks

- **social-auth-app-django 5.4.2** (CVE-2025-61783, moderate): Held at 5.4.2 to preserve Django 4.2 LTS compatibility. The fix in 5.6.0 requires Django 5.1+. A Django 5.x migration is planned.
- **pytest 8.3.3** (CVE-2025-71176, moderate): Dev-only testing dependency, not shipped to production. Upgrade to pytest 9 pending pytest-django compatibility.
