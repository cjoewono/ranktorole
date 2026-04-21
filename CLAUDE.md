# Military-to-Civilian Resume Translator

## Stack

React 18 (Vite) | Django REST Framework | PostgreSQL | Docker Compose | Nginx

## Deadline

April 24, 2026

## Service Map

**Dev (hybrid)**

- Frontend: Vite on host at `:5173` (HMR enabled), proxies `/api/` to `localhost:8000`
- Backend: Django in Docker at `:8000` (runserver, hot-reload via bind mount in docker-compose.override.yml)
- Database: PostgreSQL in Docker, service name `db`, port never exposed to host
- **Redis:** `redis:7-alpine` on internal network. `REDIS_URL=redis://redis:6379/0`. All cache ops use `django.core.cache.cache` — never import `redis-py` directly. Inspect with `docker compose exec redis redis-cli` then `KEYS rtr:*`. Tests always use LocMemCache via root conftest autouse fixture.
- Nginx: not started in dev

**Production (full Docker + TLS)**

- Frontend: `npm run build` → `dist/` → Nginx serves static from `/usr/share/nginx/html`
- Backend: Django in Docker at `:8000` (gunicorn, 3 workers)
- Database: PostgreSQL in Docker, port never exposed
- Nginx: only public-facing service; `:80` (ACME + redirect) and `:443` (TLS via Let's Encrypt); proxies `/api/` → backend, `/` → static dist

## Key Commands

### Docker

- `docker compose up` / `docker compose up --build` / `docker compose stop`
- `docker compose logs -f [frontend|backend|db]`

### Backend

- `docker compose exec backend python manage.py migrate`
- `docker compose exec backend python manage.py makemigrations`
- `docker compose exec backend pytest`

### Frontend

- `docker compose exec frontend npm run build`

### Production (EC2)

- `sudo certbot certonly --webroot -w /var/lib/letsencrypt -d ranktorole.app -d www.ranktorole.app`
- `docker compose up -d db nginx frontend`
- `docker compose run -d backend gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3`
- `docker compose exec backend python manage.py migrate`
- `sudo crontab -e` → add `0 */12 * * * certbot renew --quiet && docker compose -f /path/to/docker-compose.yml exec nginx nginx -s reload`

## Architecture

See ARCHITECTURE.md for system design patterns and Docker lessons.

## Product Flow

1. User uploads PDF resume → backend extracts text, creates Resume record, returns resume_id
2. User pastes job description → single LLM call returns draft + 1 targeted clarifying question
3. User answers questions in chat → stateful refinement turns (history persisted to DB, loaded server-side)
4. User approves → inline bullet editing → "Approve & Finalize" → `is_finalized = True`

## LLM Integration

- Provider: Claude API (`claude-sonnet-4-20250514`)
- Location: `backend/translate_app/services.py`
- Input call 1: `{military_text (string), job_description (string)}`
- Input call 2+: `{session_anchor (dict from DB), chat_history (list from DB), message (string)}`
- Output every call: JSON matching `MilitaryTranslation` schema (see below)
- Env var: `ANTHROPIC_API_KEY`
- SDK: `anthropic==0.40.0` (pinned — do not upgrade pre-deadline)

## Pydantic Schema (MilitaryTranslation)

```python
class RoleEntry(BaseModel):
    title: str
    org: str
    dates: str
    bullets: list[str]

class MilitaryTranslation(BaseModel):
    civilian_title: str
    summary: str
    roles: list[RoleEntry]
    clarifying_question: str   # single question on draft call, "" on chat turns
    assistant_reply: str       # "" on draft call, populated on chat turns
```

## URL Map

```
POST   /api/v1/resumes/upload/          PDF → military_text, returns resume_id
POST   /api/v1/resumes/{id}/draft/      JD → draft + question, sets session_anchor
POST   /api/v1/resumes/{id}/chat/       message → updated draft + reply (history loaded from DB)
PATCH  /api/v1/resumes/{id}/finalize/   final edits → is_finalized=True
GET    /api/v1/resumes/                 list resumes for authenticated user
GET    /api/v1/resumes/{id}/            retrieve single resume
DELETE /api/v1/resumes/{id}/            delete resume
POST   /api/v1/recon/brainstorm/         form-driven career brainstorm (Haiku 4.5)
POST   /api/v1/billing/checkout/        Stripe Checkout Session (Pro upgrade)
POST   /api/v1/billing/portal/          Stripe Customer Portal (manage/cancel)
GET    /api/v1/billing/status/          current tier, subscription status, usage, limits
POST   /api/v1/billing/webhook/         Stripe event receiver (signature-verified)
```

## Frontend Routes

```
/billing/success    (auth required) — post-checkout landing; polls profile until tier=pro
/billing/cancel     (auth required) — checkout cancelled notice
```

## Context Window Budget (per call)

| Layer            | Tokens     | Policy                               |
| ---------------- | ---------- | ------------------------------------ |
| System prompt    | ~400       | Static — never changes               |
| Session anchor   | ~350       | Set once on draft call, always kept  |
| DB chat history  | ≤ 500      | Loaded from DB, appended server-side |
| New user message | ~100       | Current turn only                    |
| **Total input**  | **~1,350** | Well under 5,000 token budget        |

Raw `military_text` and `job_description` are NEVER passed after call 1.

## Cost Reference

- ~$0.016 per draft call (call 1)
- ~$0.013 per refinement turn
- ~$0.055 per full session (call 1 + 3 turns)
- ~$0.025–$0.035 with prompt caching

## Conventions

### Python/Django

- PEP 8, explicit imports
- Thin views; all logic in `services.py`
- Serializers for all data transformations
- All models use UUIDv4 primary keys
- **Cache-aside pattern for new read endpoints.** New read-heavy endpoints SHOULD use the cache-aside pattern: build a cache key in the app's `cache_utils.py` module, check cache first, populate on miss. Use `django.core.cache.cache` only — never import `redis-py` directly. TTL choice: 6h for external API responses, 1h for DB-derived per-user data, 24h for slowly-changing reference data.
- **Invalidation is non-negotiable for write paths.** Any cached read endpoint backed by a model MUST have its cache invalidated by every write path on that model. Add an `invalidate_*_cache()` helper in the app's `cache_utils.py` and call it after every `save()` / `delete()` / `bulk_update()`. Per-user caches are keyed by `user.pk` (UUID); never key by email or username (mutable).
- **Don't cache failures.** Empty upstream responses, 404s, 5xx mocks, and validation failures must NOT be cached. The standard pattern is `if data: cache.set(...)` — do NOT use `cache.set(key, payload)` unconditionally on the success branch.
- **Cache utilities live in `<app>/cache_utils.py`.** Each Django app that uses caching has its own `cache_utils.py` module containing key-builder functions, TTL constants, and invalidation helpers. Views import from this module — never inline cache key strings or TTL literals in views.

### React

- Functional components + Hooks
- Tailwind for all styling
- React Router DOM for navigation
- Lazy load heavy components
- Frontend state machine: IDLE → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE

### API

- RESTful: pluralized nouns, e.g. `/api/v1/resumes/`
- JWT auth on all endpoints except `/api/v1/auth/` and `/api/v1/billing/webhook/`
- multipart/form-data on upload endpoint only; JSON everywhere else

## O\*NET API (authenticated v2)

- Base URL: `https://api-v2.onetcenter.org`
- Auth: `X-API-Key` header (key from `ONET_API_KEY` env var)
- Purpose: map military occupation codes to civilian job titles; used internally by `recon_app`
- Server-side only, never call from frontend
- Public routes removed after Recon rebuild (April 2026). O\*NET is now a support library for `recon_app`'s brainstorm pipeline — `onet_app` exports `ONET_BASE`, `_onet_headers()`, `_normalize_career_data()`, and shared helpers from `recon_enrich_service.py`.

## OAuth

- Provider: Google OAuth 2.0
- Library: `social-auth-app-django==5.4.2` (pinned — 5.6.0 requires Django 5.1)
- Purpose: satisfies "secret key with OAuth" requirement
- Env vars: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`
- Endpoints: `GET /api/v1/auth/google/`, `POST /api/v1/auth/google/callback/`

## Billing (Stripe)

- Checkout: Stripe-hosted only — our frontend never sees a card number
- Tier changes: server-side only, via the `StripeWebhookView` (signature-verified)
- `stripe_customer_id` is the only Stripe reference persisted
- Audit log: every status transition writes a `SubscriptionAuditLog` row (append-only, unique `stripe_event_id` for idempotency)
- Env vars: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, `STRIPE_CHECKOUT_SUCCESS_URL`, `STRIPE_CHECKOUT_CANCEL_URL`
- Profile page (`/profile`) hosts Manage Billing (Pro) and Upgrade to Pro (Free) buttons.
- `PortalSessionView` enforces a `return_url` allowlist: `https://ranktorole.app/*` or `http://localhost:*`. Other URLs return 400.
- Production security headers (HSTS, SSL redirect, secure cookies, X-Frame-Options DENY) are gated on `not DEBUG` in `settings.py`.

## Common Pitfalls

- **Env changes require `--force-recreate`.** `docker compose restart backend` bounces the process inside the existing container without re-reading `.env` — environment variables are frozen at container creation time. To pick up `.env` changes: `docker compose up -d --force-recreate backend`. Symptom of the bug: app reports cache/db as healthy but no keys land in Redis (because Django falls back to LocMemCache when `REDIS_URL` is missing from env).

## Hard Rules

- Do not add packages without asking
- Do not change model field names
- Do not run `docker compose down` (use `stop`)
- Do not modify `docker-compose.yml` or `.env` without instruction
- Do not create new Django apps without confirming the name
- See SECURITY.md before touching auth, API keys, or user data
- Check TASKS.md before starting any work
- User layer files (`.env`, `docker-compose.yml`, `migrations/`) are read-only unless explicitly told otherwise
- Raw PDF bytes are never stored — extracted text only
- `chat_history` is persisted to DB server-side — the backend loads it on every call. **Never pass history in the request body — it is ignored.**
- Never handle card data. Stripe-hosted Checkout is the only path a PAN/CVV can enter the system. If a frontend task ever calls for a card input field, stop and flag it.
- The webhook endpoint (`/api/v1/billing/webhook/`) must run `stripe.Webhook.construct_event` before any DB work. Do not add logic between the `request.body` read and the signature check.
- User tier (`free` / `pro`) is writable only through the Stripe webhook. Do not expose tier in any writable serializer; `UserSerializer` keeps it in `read_only_fields`.
- Never weaken `_SYSTEM_PROMPT`'s preservation rules without explicit discussion. Rules exist because smoke tests caught specific failures: metric-erasure (Task 4), aggregate fabrication (Task 5), proper-noun generalization (Task 6). Regression means veterans lose resume quality in ways tests don't catch.
- The TAILORING RULES (T1–T5) and the ATS ASSESSMENT format spec in `_SYSTEM_PROMPT` are part of the same contract as the preservation rules. They work together: preservation rules define the hard facts; tailoring rules define the framing and vocabulary. Changing either without the other risks either (a) blander cosmetic translation or (b) tailoring pressure that the grounding validator has to catch at the flag layer. Real-resume smoke testing (Brandon/Unstructured) is the acceptance test for any change to either section.
- v2 of the tailoring prompt rebalanced the authority gradient: REWRITE is the primary task, PRESERVATION is the constraint. A bullet that comes back nearly identical to the source is a FAILED rewrite. Per-role identity (P3) allows identity markers to appear once per role rather than in every bullet. R3 splits vocabulary use into three explicit cases. The prompt contains three demonstrated bullet transformations (Example 1/2/3) that are load-bearing for output quality — do not remove them without replacement.
- v2.1 extended R3 to cover noun-phrase mirroring, not just verb rewrites. R3(c) now includes the implied-responsibility guardrail (budget management ≠ P&L management). Example 4 in the prompt demonstrates both the positive behavior and the guardrail with 'What stayed limited' commentary. Do not drop Example 4 — its negative-space teaching is how Claude learns the bright line without adding a rule.
- v2.2 promoted guardrails OUT of R3's carve-out clauses and into a standalone HARD LIMITS block with four enumerated limits (H1-H4) covering P&L-class phrases, aggregate totals, fabricated credentials, and grounded ATS Strong matches. HARD LIMITS sits BEFORE PRESERVATION RULES in prompt order — authority gradient matters. When adding future guardrails to the prompt, do not add them as exception clauses inside a positive rule. Add them to HARD LIMITS as an enumerated H-rule with concrete phrase examples.
- `bullet_flags` and `summary_flags` are response-only — do not persist to DB, do not store on Resume model. They regenerate on every Draft and Chat call using current `military_text`.
- The honesty stack's three layers are coupled. If you change the Pydantic schema, update `grounding.py` too. If you change response shape, update DATA_CONTRACT.md and the frontend `useResumeMachine` reducer that stores `bulletFlags`/`summaryFlags`.
- `flag_unearned_claims` in `grounding.py` is the deterministic enforcement layer for claim-class violations that Layer 1 (prompt) cannot reliably hold. Four categories: P&L-class (always flagged), unearned skills (source-check), unearned credentials (source-check), aggregate dollar fabrications (source-check). Before adding a new phrase to any of the four blocklists, add a matching test to `TestUnearnedClaimsValidator`. Before relaxing a blocklist entry, review whether a real-resume smoke test justified the relaxation — false positives on common civilian phrases are a real risk, but so is silent regression on honesty guarantees.
- Recon enrichment must never call Haiku without first resolving the MOS title via `_resolve_mos_title()`. An empty resolved title is a valid input — the prompt has explicit "do not invent" handling for that case. Never pass a bare MOS code to Haiku for interpretation.
- The MOS title resolver checks local dicts (`NAVY_OFFICER_DESIGNATORS`, `COAST_GUARD_RATINGS`) FIRST, then O*NET with exact-match, then O*NET with prefix-match (AF/USSF only). Never reorder this priority without updating tests.
- Recon is profile-decoupled. Never read `request.user.profile_context` from `recon_app` views or services.
- `recon_app` has no models. Do not add one without revisiting the capstone CRUD-model scope.
- Haiku picks are validated against the O\*NET baseline in `recon_app.services.run_brainstorm` — never trust a code the model returns without checking it against the baseline list.
