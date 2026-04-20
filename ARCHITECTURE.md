# Architecture — Military-to-Civilian Resume Translator

## Docker/Nginx Pattern

- All API calls use relative paths (`/api/v1/...`), never hardcoded hosts
- Nginx handles routing: `/api/` → `backend:8000`, `/` → static `dist/`
- New env vars require `docker compose down && up` (restart insufficient)
- Migrations must re-run after full down/up cycle

## Django App Structure (from BridgeBoard)

- Each feature = its own Django app (`translate_app`, `user_app`, `contact_app`, `onet_app`)
- Namespace apps in `urls.py` to avoid endpoint collisions
- `services.py` handles all external API and LLM calls
- Views only handle request/response, nothing else

## Product Flow Architecture

### Phase 1 — PDF Ingestion

```
Frontend (dropzone) → multipart/form-data → POST /api/v1/resumes/upload/
  → validate MIME type + magic bytes + size (10MB cap)
  → PyMuPDF extracts text
  → Resume.objects.create(military_text=extracted, user=request.user)
  → returns {id, created_at}
```

Raw PDF bytes are never stored. Extracted text only.

### Phase 2 — Double-Duty Draft Call

```
Frontend → POST /api/v1/resumes/{id}/draft/ {job_description}
  → loads Resume by id + user (scoped)
  → calls call_claude_draft(military_text, job_description)
      → single Claude API call
      → returns MilitaryTranslation (draft + clarifying_question)
  → saves to Resume: job_description, session_anchor, civilian_title, summary, roles, ai_initial_draft
  → returns full MilitaryTranslation to frontend
Frontend splits response:
  → left pane: civilian_title + summary + roles (with bullets)
  → right pane: clarifying_question rendered as a chat message
```

### Phase 3 — Stateful Refinement Loop

```
Frontend → POST /api/v1/resumes/{id}/chat/
  {
    "message": "I want to emphasize the Trust & Safety angle"
  }
  → loads Resume.session_anchor and chat_history from DB
  → builds messages: system_prompt + anchor + history + new message
  → calls Claude API
  → returns MilitaryTranslation (updated draft, assistant_reply="...")
  → saves updated civilian_title, summary, roles to Resume
  → appends new turn to chat_history, increments chat_turn_count
  → returns full MilitaryTranslation to frontend
Frontend:
  → left pane live-updates with new draft
  → right pane appends assistant_reply as a chat message
```

**Key:** raw `military_text` and `job_description` are never sent again after Phase 2.
**Key:** chat history is persisted to DB — backend loads it from DB on every call.

### Phase 4 — Finalization

```
Frontend → PATCH /api/v1/resumes/{id}/finalize/
  {
    "civilian_title": "...",  # may include user's inline edits
    "summary": "...",
    "roles": [...]
  }
  → saves final state to Resume
  → sets Resume.is_finalized = True
  → returns finalized Resume
Frontend:
  → clears chat history state
  → redirects to /dashboard
```

## Claude API Integration Pattern

- Use `anthropic` Python SDK (pinned at 0.40.0)
- Pydantic model validates every response (fail-fast on bad JSON)
- Schema: `MilitaryTranslation(civilian_title, summary, roles, clarifying_question, assistant_reply)`
- Never call Claude API directly from views — always via `services.py`
- Response parsed from text block only, never tool_use block
- Markdown fences stripped before JSON parse
- `strip_tags()` applied to every string field before persistence (stored-XSS defense)

## Context Window Management

Every Claude API call stays under 5,000 tokens:

| Layer            | Content                         | Tokens     | Policy                               |
| ---------------- | ------------------------------- | ---------- | ------------------------------------ |
| System prompt    | Role + output instructions      | ~400       | Static, never changes                |
| Session anchor   | Compressed JD + resume identity | ~350       | Set once on draft call               |
| DB chat history  | Recent chat turns               | ≤ 500      | Loaded from DB, appended server-side |
| New user message | Current turn                    | ~100       | Current turn only                    |
| **Total**        |                                 | **~1,350** |                                      |

`call_claude_draft()` runs ONCE on the draft call. After that:

- Raw `military_text` (~1,400 tokens) → never sent again
- Raw `job_description` (~500 tokens) → never sent again
- `session_anchor` (~350 tokens) → loaded from DB on every subsequent call

## Resume Model

```python
class Resume(models.Model):
    id                = UUIDField(primary_key=True)
    user              = ForeignKey(User)
    military_text     = TextField()                      # extracted PDF text
    job_description   = TextField(blank=True)            # set on draft call
    session_anchor    = JSONField(null=True, blank=True) # set on draft call
    civilian_title    = CharField(max_length=255, blank=True)
    summary           = TextField(blank=True)
    roles             = JSONField(default=list)          # set on draft, updated on chat
    chat_history      = JSONField(default=list)          # populated by backend on every chat turn
    chat_turn_count   = PositiveIntegerField(default=0)  # per-resume chat quota (Free/Pro)
    ai_initial_draft  = JSONField(null=True, blank=True) # set on draft, used for redline diff
    approved_bullets  = JSONField(default=list)          # reserved for future granular approval
    rejected_bullets  = JSONField(default=list)          # reserved for future granular rejection
    is_finalized      = BooleanField(default=False)      # set True on finalize call
    created_at        = DateTimeField(auto_now_add=True)
    updated_at        = DateTimeField(auto_now=True)
```

Fields are `blank=True` on partial fields because upload creates the record before the draft call.

## Frontend Architecture

### AppShell Pattern

`App.jsx` renders an `AppShell` component that owns the persistent NavBar and mounts all
pages once. Pages are shown/hidden via CSS (`hidden` class) rather than unmounted — this
prevents NavBar remounts and eliminates layout flash when ResumeBuilder enters fullscreen.

```
App
└── AppShell
    ├── NavBar (always mounted)
    ├── <ForgeSetup />       (hidden when path ≠ /profile)
    ├── <CareerRecon />      (hidden when path ≠ /recon)
    ├── <Dashboard />        (hidden when path ≠ /dashboard)
    ├── <Contacts />         (hidden when path ≠ /contacts)
    └── <ResumeBuilder setFullscreen={...} />  (hidden when path ≠ /resume-builder)
```

`fullscreen` state lives in AppShell and is passed as `setFullscreen` to ResumeBuilder.
When the builder enters a split-pane phase, it calls `setFullscreen(true)` — AppShell
applies `overflow-hidden` to prevent body scroll during the split-pane layout.

### Career Recon

O\*NET-powered career exploration tool at `/recon`. Three-phase UI:
SEARCH → RESULTS → DETAIL. Serves as a conversion funnel into the resume builder.

**O\*NET layer** — pure server-side proxy to O\*NET's My Next Move for Veterans API.
Three views in `onet_app`: `OnetMilitarySearchView` (military search),
`OnetCareerDetailView` (aggregated career report), `ReconEnrichView` (Haiku enrichment).
All search/detail views use `OnetThrottle`. Enrichment uses `ReconEnrichThrottle`.
O\*NET v2 API (`https://api-v2.onetcenter.org`) with `X-API-Key` auth (env: `ONET_API_KEY`).

**Enrichment layer** — `POST /api/v1/onet/enrich/` adds personalized career intelligence
via Claude Haiku 4.5. O\*NET data and `profile_context` are combined into a single Haiku
call. Five cost controls defend the feature (defense in depth):

1. Auth + profile gate — `IsAuthenticated` + non-empty `profile_context` required
2. Per-user tiered throttle — `ReconEnrichThrottle` (15/day free, 25/day pro)
3. DB-backed result cache — profile-aware SHA256 keys, 7-day TTL; cache hit = $0
4. Hard API timeout — 15s ceiling on Haiku call (P95 ~3s)
5. Global daily ceiling — 500 calls/day max; endpoint returns 503 beyond that

**Shared normalization** — `_normalize_career_data()` helper is used by both
`OnetCareerDetailView` and `ReconEnrichView` to parse O\*NET v2 response shapes.

**Max spend/day:** $0.04 free / $0.065 pro per user; $1.30 global ceiling.
**Expected spend at 100 pro users / 10 sessions/month:** ~$3/month with 60-75% cache hit rate.

**Deliberately excluded:** resume bullets. Resume builder is where veterans draft bullets
with their real numbers. LLM-fabricated XYZ metrics on Recon is a liability not taken on.

### MOS Title Resolution

O\*NET has uneven coverage of military codes:

- Navy officer designators are entirely unindexed
- Air Force / Space Force officer AFSCs are only indexed at full-specialty
  granularity (11F1B, not 11F)
- Coast Guard is entirely unindexed
- Army, Marine Corps, and enlisted Navy/AF resolve cleanly

`_resolve_mos_title()` handles these gaps with layered priority: local dicts
first (Navy officers, CG ratings), then O\*NET exact match, then O\*NET prefix
match (AF/USSF only, with sub-specialty stripping). Titles cached 30 days.

The resolver returns empty string on miss — an intentional sentinel the
enrichment prompt recognizes as "known unknown" and will not fabricate around.

### State Machine Hook

All resume builder logic lives in `frontend/src/hooks/useResumeMachine.js`:

- `initialState` — 9-field initial state
- `reducer` — 18 action cases
- `useEffect` — re-entry from Dashboard via `?id=&mode=` search params
- `handleGenerateDraft` — `useCallback`-wrapped, calls `generateDraft()` API
- `handleChatSend` — `useCallback`-wrapped, calls `sendChatMessage()`, dispatches optimistic + received actions

`ResumeBuilder.jsx` is JSX-only — it calls `useResumeMachine()` and passes results to children.

### State Machine Phases

```
IDLE        → upload dropzone visible, no resume_id in state
UPLOADED    → resume_id in state, JD textarea + "Generate Draft" button visible
LOADING     → re-entry from Dashboard: loading spinner while fetching resume from DB
DRAFTING    → loading spinner, both panes empty
REVIEWING   → split pane: draft left, chat right, "Approve & Finalize" button visible
FINALIZING  → inline bullet editing enabled, "Confirm Final" button
DONE        → export CTA + "Back to Dashboard" link
```

Single `phase` field in state drives all conditional renders.

### DraftPane Component Tree

```
DraftPane/ (index.jsx)
├── phase === REVIEWING  → read-only role cards + "Approve & Edit" button
├── phase === FINALIZING → <FinalizingEditor />
│   ├── Title + Summary inputs
│   ├── <BulletEditor /> per bullet
│   │   ├── Accordion header (current value)
│   │   ├── Textarea (edit)
│   │   ├── <DiffView /> (vs ai_initial_draft)
│   │   └── AI suggestion chip (Accept / Dismiss)
│   └── Sticky confirm button
└── phase === DONE       → Export PDF button + Back to Dashboard link
```

## PDF Extraction

- Library: PyMuPDF (`pymupdf==1.24.11`)
- Text-native PDFs extract cleanly — no OCR needed for typical military resumes
- Two-column skills sections extract sequentially (left then right) — fine for LLM consumption
- Extraction order: page-by-page text concatenated with newline
- Raw PDF bytes discarded after extraction

## Billing & Subscription

Stripe-powered Free/Pro tiers. PCI scope is SAQ A — the application never sees
card data. All card entry happens on Stripe-hosted Checkout; our system only
stores a `stripe_customer_id` reference and listens for webhook events.

### Components

- **`user_app/billing_services.py`** — thin Stripe SDK wrapper. `_configure()`
  sets the API key lazily so tests that monkeypatch settings work. All
  create-side calls (`Customer`, `Checkout.Session`, `billing_portal.Session`)
  pass an idempotency key bound to the user plus a UUID, so a single client
  action cannot produce duplicate Stripe objects on network retry.
- **`user_app/billing_views.py`** — four endpoints:
  - `CheckoutSessionView` — creates the Checkout Session for Pro upgrade
  - `PortalSessionView` — opens the Customer Portal for manage/cancel
  - `BillingStatusView` — returns `{tier, subscription_status, usage, limits}` for frontend state
  - `StripeWebhookView` — receives events; signature-verified before any DB work
- **`user_app/billing_throttles.py`** — `CheckoutThrottle` (5/min) defeats card-testing / botting on the upgrade path
- **`SubscriptionAuditLog`** — append-only model that records every status transition. `stripe_event_id` is the unique key; replays short-circuit

### Status → Tier Mapping

The webhook handler translates Stripe subscription status into our tier:

| Stripe status                                                        | Our tier                         |
| -------------------------------------------------------------------- | -------------------------------- |
| `active`, `trialing`, `past_due`                                     | `pro` (past_due is grace period) |
| `incomplete`, `incomplete_expired`, `canceled`, `unpaid`, `inactive` | `free`                           |

### Webhook Flow

```
POST /api/v1/billing/webhook/
  → verify_webhook(payload, signature)    # raises on bad sig → 400
  → stripe_event_id already in SubscriptionAuditLog?
        yes → return 200 {received, duplicate}     # idempotent
  → dispatch on event.type:
        checkout.session.completed            → _apply_status('active')
        customer.subscription.updated|created → _apply_status(event.data.status)
        customer.subscription.deleted         → _apply_status('canceled')
  → _apply_status runs under select_for_update + transaction.atomic:
        update User.subscription_status, User.tier
        append SubscriptionAuditLog row
```

### Daily Usage Counters

`User.resume_tailor_count` + `User.last_reset_date` track daily quota for free
tier. The counter resets at UTC midnight on first hit (lazy reset — no cron).
`Resume.chat_turn_count` tracks per-resume chat quota so a single conversation
cannot drain a user's whole daily allowance.

These counters feed two custom DRF permissions in `user_app/permissions.py`:

- `IsProOrUnderLimit` — daily-resetting per-user counter; views opt in with `counter_field = 'resume_tailor_count'`
- `ChatTurnLimit` — permanent per-resume counter against `settings.FREE_TIER_CHAT_LIMIT`

Pro users (`subscription_status ∈ {active, trialing, past_due}` and `tier == 'pro'`) bypass both.

### What We Never Store

- Card numbers, expiries, CVVs — never transmitted through our servers
- Stripe secret key outside of `.env`
- Payment methods, invoices, or any PII beyond what Stripe sends in webhook metadata

## Known Lessons

- `docker compose restart` does NOT re-read `env_file` — environment is frozen at container creation. To pick up `.env` changes: `docker compose up -d --force-recreate backend`. Symptom: app appears healthy but no keys land in Redis (Django silently fell back to LocMemCache because `REDIS_URL` was missing from env).
- Use `PersistentClient` pattern for any local storage services
- Relative paths only — hardcoded IPs break in Docker networking
- `chat_history` IS persisted to DB — backend owns it; never pass it in request body
- multipart/form-data on upload endpoint only — JSON everywhere else
- AppShell pattern (CSS hide/show) prevents NavBar remounts and fullscreen flash
- Vite resolves directory imports to `index.jsx` — use this for component subfolders
- Custom hooks (`useResumeMachine`) keep page components as pure JSX; easier to test and reason about
- Stale Docker containers cause phantom bugs — always check for orphaned containers (`docker ps -a`) when behavior doesn't match code

## Cache Strategy

Redis is the cache backend for all `django.core.cache.cache` operations.
Key prefix `rtr` (set in `CACHES.OPTIONS.KEY_PREFIX`) namespaces all entries.
Tier-aware throttle keys, response caches, and global counters share one
Redis instance with 256mb LRU eviction.

| Key pattern                   | Purpose                                                                                                 | TTL               | Invalidation                               |
| ----------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------- | ------------------------------------------ |
| `rtr:1:throttle_*`            | DRF tiered throttle counters (upload, draft, chat, finalize, onet, recon_enrich)                        | 24h (rate window) | TTL-only                                   |
| `rtr:1:health_probe`          | Health endpoint set/get round-trip                                                                      | 10s               | TTL-only                                   |
| `rtr:1:mos_title:*`           | O\*NET veteran MOS title lookup (NAVY_OFFICER_DESIGNATORS, COAST_GUARD_RATINGS, O\*NET prefix matching) | 30 days           | TTL-only                                   |
| `rtr:1:recon_enrich:*`        | Per-career Haiku enrichment payload, profile-fingerprinted                                              | 7 days            | TTL-only                                   |
| `rtr:1:recon_enrich_global:*` | Daily global ceiling counter (atomic INCR)                                                              | 24h               | TTL-only                                   |
| `rtr:1:onet_search:*`         | OnetSearchView response payload                                                                         | 6h                | TTL-only; not cached if empty              |
| `rtr:1:onet_military:*`       | OnetMilitarySearchView response payload                                                                 | 6h                | TTL-only; not cached if empty              |
| `rtr:1:onet_career:*`         | OnetCareerDetailView normalized career data                                                             | 6h                | TTL-only; not cached on 404                |
| `rtr:1:resume_list:*`         | Per-user resume list endpoint response                                                                  | 1h (safety net)   | **Explicit** — cleared by every write path |

**Cache-aside pattern.** All response caches use the cache-aside (lazy-load)
pattern: read from cache, fall back to DB or upstream on miss, populate cache
on success. This pattern is correct for read-heavy data with infrequent writes.

**Invalidation discipline.** The resume list cache is the only entry with
explicit invalidation — TTL is a safety net, not the primary freshness
mechanism. All six Resume write paths call `invalidate_resume_list_cache(user)`
immediately after `resume.save()` or `resume.delete()`. Per-user isolation
guaranteed by user PK in the cache key.

**Failure mode.** `IGNORE_EXCEPTIONS=False` means Redis outages surface as
500 errors on cache-touching requests rather than silent throttle bypass.
Healthcheck catches outages within 5 seconds. Tradeoff documented in
PROJECTLOG.md Session 15.

## Tiered Throttling

Rate limits are tier-aware. Every throttled endpoint reads `request.user.tier` (free/pro) and looks up the rate from `settings.TIERED_THROTTLE_RATES[scope][tier]`.

| Scope              | Free   | Pro    | Endpoints                                                   |
| ------------------ | ------ | ------ | ----------------------------------------------------------- |
| `user_upload`      | 3/day  | 15/day | POST /api/v1/resumes/upload/                                |
| `user_draft`       | 1/day  | 5/day  | POST /api/v1/resumes/{id}/draft/                            |
| `user_chat`        | 10/day | 50/day | POST /api/v1/resumes/{id}/chat/                             |
| `user_finalize`    | 3/day  | 15/day | PATCH /api/v1/resumes/{id}/finalize/                        |
| `user_onet`        | 10/day | 30/day | GET /api/v1/onet/{search,military,career}/                  |
| `billing_checkout` | 5/min  | 5/min  | POST /api/v1/billing/{checkout,portal}/ (anti card-testing) |

All tiered throttle classes live in `translate_app/throttles.py`. The
`billing_checkout` throttle lives in `user_app/billing_throttles.py`. Cache key
includes tier so upgrade/downgrade immediately takes effect. Falls back to
`DEFAULT_THROTTLE_RATES` for unknown tiers.

## Service Map

| Service  | Image          | Role                                                      | Network                                                 |
| -------- | -------------- | --------------------------------------------------------- | ------------------------------------------------------- |
| db       | postgres:16    | Primary datastore (users, resumes, audit log)             | internal only                                           |
| redis    | redis:7-alpine | Cache backend — throttles, enrichment results, MOS titles | internal only; 6379 exposed to host in dev via override |
| backend  | ./backend      | Django/gunicorn API server                                | internal only                                           |
| frontend | node:20-alpine | Vite build → static dist                                  | internal only                                           |
| nginx    | nginx:alpine   | Public edge: :80/:443, proxies /api/ → backend, / → dist  | internal + host ports 80/443                            |

- **redis** — Redis 7 in-memory cache. Stores throttle counters (24h TTL, tier-namespaced), MOS title cache (30-day TTL), Recon enrichment results (7-day TTL, profile-fingerprinted), global daily ceiling counter (atomic INCR). 256mb LRU cap, RDB snapshots only (cache data, not source-of-truth). Internal network; host port 6379 exposed in dev via override.

## Dev vs Production

### Development

- Frontend: `npm run dev` on host (`localhost:5173`, HMR enabled)
- Backend: `docker compose up` (`localhost:8000`)
- Redis: `docker compose up` starts it alongside db + backend
- Vite proxies `/api/` to `localhost:8000` via `vite.config.js`
- No Nginx needed in dev

### Production

- `npm run build` → `dist/`
- `docker compose up --build`
- Nginx serves `dist/` and proxies `/api/` → `backend:8000`

## Honesty Stack

Three layers of validation protect against LLM fabrication and identity
erasure in the resume translation flow. Built April 17 2026 in response
to the product question: how do we ensure translations are both optimally
written for recruiters AND honestly grounded in what the veteran actually
did?

### Layer 1 — Prompt Guardrails (`translate_app/services.py`)

`_SYSTEM_PROMPT` contains 8 non-negotiable rules:

1. Preserve every concrete source fact (dollar amounts, percentages, team
   sizes, named scope) when translating the bullet that contains them
2. Never add concrete facts not in source — including aggregates computed
   across source numbers (no "$1.2M total" when source lists $275K, $240K,
   $25K separately)
3. Preserve ALL proper nouns verbatim — named operations (Ukraine, OIF),
   programs (ION, Palantir), specialties (PSYOP, SIGINT, red-team),
   locations, partner forces (UK, Canada, Tier 1 SOF), clearances
   (TS/SCI), certifications (COR, MILDEC). Generalization destroys ATS
   discoverability and career identity
4. Never inflate scope or seniority beyond source
5. Preserve employer/command context — prefix parent org into each role's
   `org` field (e.g., three Army deployments all carry
   `US Army Special Operations, PSYOP — ...`)
6. Jargon-vs-identity boundary: translate BLUF/S-4/MOS codes, do NOT
   translate PSYOP/SIGINT/red-team/USSOCOM/Ukraine
7. Summary fidelity — preserve multi-domain differentiation signals, no
   generic PM boilerplate
8. Use strong past-tense civilian action verbs but the underlying facts
   (numbers, proper nouns, named operations) must remain intact

### Layer 2 — Grounding Validator (`translate_app/grounding.py`)

Pure-Python regex validator. Zero LLM calls. Deterministic. Three
entry points:

- `flag_bullet(bullet, source_text)` — scans one bullet for numeric claims
  (regex `_NUMERIC_PATTERN`) and scope-inflation verbs (`_SCOPE_VERBS`
  tuple) that appear in output but not source
- `flag_translation(roles, source_text)` — walks every bullet across all
  roles; returns list of `{role_index, bullet_index, flags}` entries,
  only including bullets with at least one flag
- `flag_summary(summary, source_text)` — reuses `flag_bullet` logic on
  the summary field; returns flat `list[str]` of flag messages

Wired into `ResumeDraftView` and `ResumeChatView`. Response includes:

- `bullet_flags: list` — from `flag_translation()`
- `summary_flags: list` — from `flag_summary()`

Flags are response-only; not persisted to DB. Regenerated on every draft
and every chat turn using current `resume.military_text` as source.

### Layer 3 — Flag-Gated Verification UX

`frontend/src/components/DraftPane/`:

- **BulletEditor.jsx** — collapsed row shows ⚠ badge (text-amber-400)
  when `flags.length > 0`. Expanded view shows "Grounding Check" panel
  listing flag messages and "I verified this bullet's claims" checkbox.
  Unflagged bullets show no checkbox — trusted by default.
- **FinalizingEditor.jsx** — tracks `verifiedFlags: Set<string>`.
  Summary gets parallel treatment when `summary_flags` non-empty (panel
  - checkbox below the summary textarea, keyed as `__summary__`).
    `allFlagsResolved` computes from `totalFlagged === verifiedCount`.
    `Confirm Final` button disabled until `allFlagsResolved` is true.
    Editing any flagged item (bullet text OR summary) clears its
    verification, forcing re-attestation.
- Progress indicator: `"N of M flagged items verified"` when any flags
  present, or `"✓ All claims passed grounding checks"` when none —
  covers both bullets and summary under one umbrella.

### Verification Model

- Unflagged items require no user action (trust by default)
- Flagged items require explicit "I verified this" checkbox OR user edit
- Edit clears verification (re-attestation required)
- AI suggestion accept clears verification
- Zero flags → Confirm Final enabled immediately

### Smoke-Tested Against

Brandon Livrago real veteran resume (Army PSYOP, Ukraine operations,
Flynn Financial $110M/$200M/$410M assets) against real JD (Unstructured
Public Sector Program Manager). All source metrics preserved; all proper
nouns preserved; summary preserves multi-domain signal; zero flags fired
on fully-grounded output.

## SSL / HTTPS (Production)

- Certbot runs on EC2 host: `sudo certbot certonly --webroot -w /var/lib/letsencrypt -d cjoewono.com -d www.cjoewono.com`
- Nginx serves ACME challenge on port 80, redirects all else to 443
- SSL certs mounted read-only into Nginx container via `/etc/letsencrypt` volume
- Django trusts `X-Forwarded-Proto: https` header from Nginx (`SECURE_PROXY_SSL_HEADER`)
- HSTS, CSP, X-Frame-Options, X-Content-Type-Options all set in Nginx
- Gunicorn on EC2: override backend command at launch — `docker compose run -d backend gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3`
- Dev workflow unchanged: Vite on host, backend in Docker with runserver, no Nginx
