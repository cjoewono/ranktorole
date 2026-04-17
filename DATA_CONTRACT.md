# DATA_CONTRACT.md

---

## Phase 1 — PDF Upload

### POST /api/v1/resumes/upload/

Auth: JWT required
Content-Type: multipart/form-data

**Input**

```
file: <binary PDF>   # required, PDF only, max 10MB
```

**Output**

```json
{
  "id": "uuid",
  "created_at": "ISO8601"
}
```

**Validation Rules**

- File must be PDF (validate MIME type server-side)
- Max file size: 10MB (enforced by Nginx `client_max_body_size` and a server-side check)
- PDF magic bytes (`%PDF-`) must be present — prevents spoofed MIME types
- Extraction must return non-empty string

**Error Responses**

- 400 → missing file, wrong file type, file too large, bad magic bytes, or empty extraction result
- 401 → missing or expired JWT
- 429 → throttle exceeded (`user_upload` scope)
- 500 → unexpected extraction failure

---

## Phase 2 — Draft Generation

### POST /api/v1/resumes/{id}/draft/

Auth: JWT required
Content-Type: application/json

**Input**

```json
{
  "job_description": "string" // required, 10–15000 chars
}
```

**Output**

```json
{
  "civilian_title": "string",
  "summary": "string",
  "roles": [
    {
      "title": "string",
      "org": "string",
      "dates": "string",
      "bullets": ["string"]
    }
  ],
  "clarifying_question": "string",
  "assistant_reply": "",
  "bullet_flags": [
    {
      "role_index": 0,
      "bullet_index": 1,
      "flags": ["string"]
    }
  ],
  "summary_flags": ["string"]
}
```

`bullet_flags`: list of flagged bullets — each entry has `{role_index: int,
bullet_index: int, flags: list[str]}`. Only bullets with at least one flag
are included. Empty list means all bullets passed grounding checks.

`summary_flags`: list of flag strings for the executive summary. Empty list
means the summary passed grounding checks. Each string is a human-readable
warning about an ungrounded numeric claim or scope-inflation verb.

**Behavior**

- Loads Resume by `{id}` scoped to `request.user` (404 if not found or wrong user)
- Calls Claude API with `military_text` + `job_description`
- Saves: `job_description`, `session_anchor`, `civilian_title`, `summary`, `roles`, `ai_initial_draft` to Resume
- `clarifying_question`: 1 targeted question based on gaps between resume and JD
- `assistant_reply`: always empty string on draft call

**Validation Rules**

- `job_description`: 10–15,000 chars (enforced in view and serializer)
- `bullets`: 3-5 items per role, each begins with past-tense action verb
- `clarifying_question`: single targeted question, grounded in the actual draft and the JD gaps (always `""` on chat turns)
- `summary`: no military acronyms (MOS, SFC, SSG, etc.)
- `civilian_title`: recognized civilian job title

**Error Responses**

- 400 → missing or invalid `job_description`
- 401 → missing or expired JWT
- 403 → free-tier daily quota exhausted (`TAILOR_LIMIT_REACHED` code)
- 404 → resume not found or not owned by user
- 422 → Claude API returned unparseable or invalid response
- 429 → throttle exceeded (`user_draft` scope)
- 503 → Claude API unavailable

---

## Phase 3 — Refinement Chat

### POST /api/v1/resumes/{id}/chat/

Auth: JWT required
Content-Type: application/json

**Input**

```json
{
  "message": "string" // required — user's reply to clarifying questions (max 2,000 chars)
}
```

**Output**

```json
{
  "civilian_title": "string",
  "summary": "string",
  "roles": [
    {
      "title": "string",
      "org": "string",
      "dates": "string",
      "bullets": ["string"]
    }
  ],
  "clarifying_question": "",
  "assistant_reply": "string",
  "bullet_flags": [
    {
      "role_index": 0,
      "bullet_index": 1,
      "flags": ["string"]
    }
  ],
  "summary_flags": ["string"]
}
```

`bullet_flags`: list of flagged bullets — each entry has `{role_index: int,
bullet_index: int, flags: list[str]}`. Only bullets with at least one flag
are included. Empty list means all bullets passed grounding checks.

`summary_flags`: list of flag strings for the executive summary. Empty list
means the summary passed grounding checks. Each string is a human-readable
warning about an ungrounded numeric claim or scope-inflation verb.

**Behavior**

- Loads `Resume.session_anchor` and `chat_history` from DB (never raw `military_text` or `job_description`)
- Builds Claude payload: `system_prompt + anchor + history + message`
- Updates Resume: `civilian_title`, `summary`, `roles` with refined output
- Appends the new turn to `Resume.chat_history` and increments `Resume.chat_turn_count`
- `assistant_reply`: brief conversational confirmation from Claude
- `clarifying_question`: always empty string on chat turns (field kept in schema for consistent frontend rendering)
- History is loaded from DB on every call — the backend is the source of truth. **Any `history` key in the request body is ignored.**

**Error Responses**

- 400 → missing `message`, or `message` longer than 2,000 chars
- 401 → missing or expired JWT
- 403 → free-tier per-resume chat limit hit (`CHAT_LIMIT_REACHED` code)
- 404 → resume not found or not owned by user
- 409 → resume is already finalized (`is_finalized=True`)
- 422 → Claude API returned unparseable response
- 429 → throttle exceeded (`user_chat` scope)
- 503 → Claude API unavailable

---

## Phase 4 — Finalization

### PATCH /api/v1/resumes/{id}/finalize/

Auth: JWT required
Content-Type: application/json

**Input**

```json
{
  "civilian_title": "string", // optional — user's inline edits
  "summary": "string", // optional — user's inline edits
  "roles": [
    // optional — user's inline edits
    {
      "title": "string",
      "org": "string",
      "dates": "string",
      "bullets": ["string"]
    }
  ]
}
```

**Output**

```json
{
  "id": "uuid",
  "civilian_title": "string",
  "summary": "string",
  "roles": [
    {
      "title": "string",
      "org": "string",
      "dates": "string",
      "bullets": ["string"]
    }
  ],
  "is_finalized": true,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**Validation Rules**

- `civilian_title`: optional string, max 200 chars
- `summary`: optional string, max 3,000 chars
- `roles`: optional list, max 20 items; each item: `title` (max 200), `org` (max 200), `dates` (max 100), `bullets` (max 10 items, each max 500 chars)

**Behavior**

- All fields optional — any provided field overwrites current Resume value
- Sets `is_finalized = True`
- Once finalized, POST `/chat/` returns 409
- Finalization is not reversible via API (admin only)

**Error Responses**

- 400 → payload violates validation rules
- 401 → missing or expired JWT
- 404 → resume not found or not owned by user
- 409 → already finalized
- 429 → throttle exceeded (`user_finalize` scope)

---

## Existing Endpoints (unchanged)

### GET /api/v1/resumes/

Auth: JWT required
Returns list of all resumes for authenticated user, ordered by `-created_at`.

**Output**

```json
[
  {
    "id": "uuid",
    "civilian_title": "string",
    "summary": "string",
    "roles": [
      {
        "title": "string",
        "org": "string",
        "dates": "string",
        "bullets": ["string"]
      }
    ],
    "is_finalized": true,
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  }
]
```

### GET /api/v1/resumes/{id}/

Auth: JWT required
Returns single resume scoped to `request.user`.

### DELETE /api/v1/resumes/{id}/

Auth: JWT required
Deletes resume. Works on finalized and unfinalized resumes.

---

## Contact Endpoints

`/api/v1/contacts/` — GET, POST, PATCH, DELETE
Auth: JWT required
All queries filtered by `request.user` — no cross-user access.

---

## O\*NET Proxy

All O\*NET requests are server-side proxies to `api-v2.onetcenter.org` using the
`X-API-Key` header sourced from `ONET_API_KEY`. Never called from the frontend.
All routes use the `user_onet` throttle scope.

### GET /api/v1/onet/search/?keyword={mos_code}

Auth: JWT required
Legacy keyword search — kept for the resume builder's skills lookup.

**Output**

```json
{
  "occupations": [{ "code": "string", "title": "string" }],
  "skills": ["string"]
}
```

### GET /api/v1/onet/military/?keyword={mos}&branch={branch}

Auth: JWT required
Server-side proxy to O\*NET My Next Move for Veterans military search.

**Query params:**

- `keyword` (required): MOS code or military job title
- `branch` (optional): `army`, `navy`, `air_force`, `marine_corps`, `coast_guard`. Default: all.

**Output:**

```json
{
  "keyword": "11B",
  "branch": "all",
  "military_matches": [
    {
      "branch": "army",
      "code": "11B",
      "title": "Infantryman (Enlisted)",
      "active": true
    }
  ],
  "careers": [
    {
      "code": "47-2061.00",
      "title": "Construction Laborers",
      "match_type": "some_duties",
      "tags": { "bright_outlook": true, "apprenticeship": true },
      "preparation_needed": "First term",
      "pay_grade": "E1"
    }
  ]
}
```

Note: under the hood O\*NET v2 returns `military_match` (flat array) — our proxy
rewrites it to `military_matches` for frontend compatibility.

### GET /api/v1/onet/career/{onet_code}/

Auth: JWT required
Aggregates career overview, skills, knowledge, technology, and job outlook from
O\*NET v2.

**Output:**

```json
{
  "code": "47-2061.00",
  "title": "Construction Laborers",
  "description": "...",
  "tags": { "bright_outlook": true },
  "skills": [{ "name": "...", "description": "..." }],
  "knowledge": [{ "name": "...", "description": "..." }],
  "technology": [
    { "category": "...", "examples": [{ "name": "...", "hot": false }] }
  ],
  "outlook": {
    "category": "Bright",
    "description": "...",
    "salary": {
      "annual_median": "40000",
      "annual_10th": "30000",
      "annual_90th": "55000"
    }
  }
}
```

Note: the proxy normalizes v2 field differences internally (`what_they_do` →
`description`, `job_outlook` → `outlook`, etc.) so the public contract is stable.

---

## Auth Endpoints (no JWT required)

```
POST /api/v1/auth/register/      throttled 5/hour (RegisterThrottle, anti-enumeration)
POST /api/v1/auth/login/         throttled 5/min (LoginRateThrottle)
POST /api/v1/auth/refresh/
POST /api/v1/auth/logout/
GET  /api/v1/auth/google/
POST /api/v1/auth/google/callback/
```

Both login and register return **normalized** error messages to prevent user
enumeration:

- Login failure: `{"error": "Invalid email or password."}`
- Register failure: `{"error": "Registration failed."}`

---

## User Profile

### GET /api/v1/auth/profile/

Auth: JWT required

**Output**

```json
{
  "id": "uuid",
  "email": "string",
  "username": "string",
  "profile_context": {},
  "tier": "free",
  "subscription_status": "inactive",
  "resume_tailor_count": 0,
  "last_reset_date": "ISO8601 date or null",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

`tier`, `subscription_status`, `resume_tailor_count`, and `last_reset_date` are
read-only via this endpoint. Tier changes happen only via the Stripe webhook.

---

## Billing Endpoints (Stripe)

All endpoints live under `/api/v1/billing/`. Card data is never seen by our
system — the frontend redirects the user to Stripe-hosted Checkout; webhooks
drive tier changes server-side.

### POST /api/v1/billing/checkout/

Auth: JWT required
Throttle: 5/min (`CheckoutThrottle`, anti card-testing)

Creates a Stripe Checkout Session for the Pro subscription. Uses an idempotency
key bound to `user.id + uuid4` so a network retry doesn't produce duplicate
sessions.

**Output**

```json
{
  "id": "cs_test_...",
  "url": "https://checkout.stripe.com/c/pay/cs_test_..."
}
```

**Error Responses**

- 401 → missing or expired JWT
- 429 → throttle exceeded
- 503 → Stripe API unreachable

---

### POST /api/v1/billing/portal/

Auth: JWT required
Throttle: 5/min (`CheckoutThrottle`)

Creates a Stripe Customer Portal session so users can manage or cancel their
subscription. Creates the Stripe Customer on demand if the user doesn't have
one yet.

**Input (optional)**

```json
{
  "return_url": "https://cjoewono.com/account"
}
```

Defaults to `http://localhost:5173/account` if omitted (dev convenience).

**Output**

```json
{ "url": "https://billing.stripe.com/p/session/..." }
```

**Error Responses**

- 401 → missing or expired JWT
- 503 → Stripe API unreachable

---

### GET /api/v1/billing/status/

Auth: JWT required

Returns current tier, subscription status, today's usage counters, and (for
free tier) the daily limits. Pro users get `"limits": null`.

**Output (free tier)**

```json
{
  "tier": "free",
  "subscription_status": "inactive",
  "usage": {
    "resume_tailor_count": 0,
    "last_reset_date": "2026-04-16"
  },
  "limits": {
    "resume_tailor_count": 1,
    "chat_turn_count_per_resume": 10
  }
}
```

**Output (pro tier)**

```json
{
  "tier": "pro",
  "subscription_status": "active",
  "usage": {
    "resume_tailor_count": 0,
    "last_reset_date": "2026-04-16"
  },
  "limits": null
}
```

---

### POST /api/v1/billing/webhook/

Auth: **None** — Stripe signature header is the sole auth mechanism.
CSRF: exempt (required by Stripe).

Stripe event receiver. Verifies the `Stripe-Signature` header via
`stripe.Webhook.construct_event` before any DB work. Handles:

- `checkout.session.completed` → user becomes Pro (`_apply_status(..., 'active')`)
- `customer.subscription.updated` / `.created` → tier follows `_STATUS_TO_TIER` map
- `customer.subscription.deleted` → user reverts to Free (`canceled`)

Other event types are acknowledged but not processed.

**Idempotency:** every processed event writes a row to `SubscriptionAuditLog`
keyed by `stripe_event_id` (unique). Replays short-circuit and return
`{"received": true, "duplicate": true}`.

**Output**

```json
{ "received": true }
```

**Error Responses**

- 400 → malformed payload or invalid signature
- 500 → processing error (triggers Stripe retry; safe because the handler is idempotent above)

---

## Billing Data Model

**`User`** gains:

- `stripe_customer_id` (str, indexed) — Stripe's reference; the only Stripe ID we store
- `subscription_status` — one of: `inactive`, `active`, `past_due`, `canceled`, `incomplete`, `incomplete_expired`, `trialing`, `unpaid`
- `resume_tailor_count` (int) — daily tailor counter, resets at UTC midnight on first hit
- `last_reset_date` (date) — used by the counter reset logic

**`SubscriptionAuditLog`** (append-only):

- `id` (UUID), `user` (FK, PROTECT), `timestamp` (indexed)
- `previous_status`, `new_status`
- `stripe_event_id` (unique) — enforces webhook idempotency
- `event_type` — Stripe event type for trace

No PAN, no CVV, no payment methods — ever.

**Status → Tier mapping** (see `billing_views._STATUS_TO_TIER`):

| Stripe status                                                        | Our tier                         |
| -------------------------------------------------------------------- | -------------------------------- |
| `active`, `trialing`, `past_due`                                     | `pro` (past_due is grace period) |
| `incomplete`, `incomplete_expired`, `canceled`, `unpaid`, `inactive` | `free`                           |

---

## Resume Model Storage Rules

- `military_text`: stored (extracted from PDF — user owns their data)
- `job_description`: stored (user owns their data)
- `session_anchor`: stored (compressed context — never raw text)
- `civilian_title`, `summary`, `roles`: stored as validated LLM output, updated on every chat turn
- `chat_history`: stored in DB — backend loads and appends to it on every chat turn
- `chat_turn_count`: stored (integer counter; drives per-resume chat quota)
- `ai_initial_draft`: stored (snapshot of the first draft, used for redline diff in FINALIZING)
- `is_finalized`: stored (boolean; once true, chat endpoint returns 409)
- Raw Claude API response: never stored
- Raw PDF bytes: never stored — extracted text only
- Failed translation attempts: not stored

---

## Data Access Rules

- All Resume data scoped to authenticated user (filter by `request.user`)
- No PII in server logs (no `military_text`, no `job_description`, no bullets)
- No cross-user resume access
- No admin access to user resume content without explicit grant
- User can delete their own resumes at any finalization state
- User tier is writable only via the Stripe webhook — never via API

---

## POST /api/v1/onet/enrich/

**Auth:** Required (JWT)
**Throttle:** ReconEnrichThrottle — 15/day free, 25/day pro
**Cache:** DB-backed, 7-day TTL, profile-fingerprint key

### Request body

```json
{ "onet_code": "47-2061.00" }
```

### Response 200

```json
{
  "onet_code": "47-2061.00",
  "career_title": "Construction Laborers",
  "enrichment": {
    "match_score": 72,
    "personalized_description": "2-3 sentences referencing veteran's branch/MOS/skills.",
    "skill_gaps": ["OSHA 30-Hour Card", "PMP certification"],
    "education_recommendation": "1-2 sentences with GI Bill path where applicable.",
    "transferable_skills": ["Team leadership", "Risk assessment", "Equipment operation", "Safety protocols"]
  }
}
```

### Error responses

| Status | When |
|--------|------|
| 400 | `onet_code` missing, malformed, or user has no `profile_context` |
| 401 | Unauthenticated |
| 404 | O*NET career code not found |
| 429 | Per-user throttle exceeded |
| 502 | O*NET API unreachable |
| 503 | Global daily ceiling hit or Haiku API failure |

### Storage rules

- Enrichment result is NEVER persisted to the Resume model or any DB table
- `profile_context` is read from `request.user` — never from request body
- Cache key: `recon_enrich:{onet_code}:{profile_fingerprint[:16]}`
- Profile fingerprint: SHA256 of `branch|mos|target_sector|sorted(skills)`
- Cached dict expires after `RECON_ENRICH_CACHE_TTL` seconds (default: 604800)
