RankToRole — Project Log

---

## April 22, 2026 | refactor(frontend): add useContacts context to mirror useResumes pattern

Added `ContactsContext.jsx` mirroring `ResumeContext.jsx`. Removed `useEffect`-based fetch from `Contacts.jsx`; data now flows through `useContacts()` hook. Mutator helpers (`createContact`, `updateContact`, `deleteContact`) live in the context with optimistic state updates and revert-on-error for deletes. `ContactsProvider` mounted in `App.jsx` alongside `ResumeProvider`. Both 234 backend tests and frontend build confirmed clean.

---

## April 22, 2026 | fix(frontend): removed orphan fetchOnetSkills call from ForgeSetup

**Status:** ✅ Complete

The `/api/v1/onet/search/` endpoint was deleted in the April 21 Recon rebuild but `ForgeSetup.jsx` still called it on MOS field blur, generating repeated 404s in production logs and showing a misleading "Leave field to auto-load matching skills from O\*NET" hint. Removed: `fetchOnetSkills` function, `handleMosBlur` async handler, three state declarations (`onetSkills`, `loadingSkills`, `onetFetched`), `onBlur={handleMosBlur}` attribute from the MOS input, and the preset-tag/loading-spinner JSX block. Updated the MOS helper text to "Optional. Used to inform civilian skill mapping." Selected skills chip display now renders from `selectedSkills` directly (was `customOnlySkills`, which was always identical since `onetSkills` was always `[]`). Manual skill addition path (`customSkill`/`addCustomSkill`) preserved unchanged. Backend test count unchanged at 234.

---

## April 22, 2026 | Removed Callsign field from Register form; auto-derive username server-side

**Status:** ✅ Complete

Removed the Callsign input field from `Register.jsx`. Username is now derived server-side in `RegisterSerializer` from the email's local-part via `_derive_unique_username()`. Collisions are resolved by appending a numeric suffix (`jdoe-2`, `jdoe-3`, …). The user-facing callsign concept lives only in `profile_context`, collected during ForgeSetup — no more duplicated concept at registration. `UserSerializer` still exposes `username` in auth responses (backend identifier only, never displayed in UI). Frontend: removed `username` state, Callsign `<div>`, and `username` from `registerRequest`. Backend: reduced `RegisterSerializer.fields` to `['email', 'password']`. Updated 7 existing register tests to drop username from request bodies. Added 1 collision test. Test count: 233 → 234.

---

## April 22, 2026 | Register auto-login via loginWithToken

**Status:** ✅ Complete

`Register.jsx` now calls `loginWithToken(data.access, data.user)` immediately after a successful 201 from `registerRequest`, then routes to `/profile` (ForgeSetup) for new users or `/dashboard` if `profile_context` is already populated. Eliminates the register → /login → re-authenticate → /profile detour. Reuses existing `AuthContext.loginWithToken` infrastructure — the same helper already used by the Google OAuth callback. No backend changes; `registerRequest` already returned the `{ user, access }` shape via `apiFetch`. Test count unchanged at 233.

---

## April 22, 2026 | \_build_auth_response helper extraction

**Status:** ✅ Complete

Extracted `_build_auth_response()` helper in `user_app/views.py`. Deduped 3 auth response sites (RegisterView 201, LoginView 200, GoogleCallbackView 200). `RefreshToken` construction, `UserSerializer` call, and `_set_refresh_cookie` now live in one place — adding a field to the auth response is a single-file change. Test count unchanged at 233.

---

## April 22, 2026 | formatDate utility extraction

**Status:** ✅ Complete

Extracted `formatDate` to `frontend/src/utils/formatDate.js`. Deduped Dashboard + Contacts. Uppercase variant exposed via opts (`{ uppercase: true }`). Dashboard call sites unchanged; Contacts call sites updated to pass `{ uppercase: true }`.

---

## April 22, 2026 | TacticalLabel + TacticalSelect hoisted to components/forms/

**Status:** ✅ Complete

Hoisted `TacticalLabel` (formerly `FieldLabel`) and `TacticalSelect` from `ForgeSetup.jsx` to `frontend/src/components/forms/`. Both files export named + default. `TacticalLabel` accepts optional `htmlFor` for accessibility linkage; `TacticalSelect` accepts optional `id` and `name` for the same reason. Migrated ForgeSetup (9 labels + 2 selects), Login (2 labels), and Register (3 labels). Contacts and CareerRecon migration deferred post-launch — their form layouts diverge (avatar logic, branch dropdown). Test count unchanged at 233.

---

## April 22, 2026 | CSS Utility — `.label-tactical`

**Status:** ✅ Complete

Added `.label-tactical` utility class to `frontend/src/index.css` under `@layer components`. Expands to `font-label text-xs tracking-widest uppercase`. Class only — no consumer migration in this commit. 136 existing occurrences across 20 files will adopt it opportunistically during natural component edits.

---

## April 21, 2026 | Stripe Frontend + Backend Hardening + Webhook E2E Verification

**Status:** ✅ Complete

Five commits: `26d1be2` (billing success/cancel routes + AuthContext.refreshUser polling), `de96400` (Subscription section on Profile — Manage Billing for Pro, Upgrade for Free), `79abda6` (throttle scoping fix), `8245214` (backend hardening + tier integrity + launch docs), `c622726` (.env.example production overrides).

**Throttle scoping fix — real launch bug.** Anon 100/day throttle was being labeled `DAILY_LIMIT_REACHED`, blocking first-time visitor registration with a 75k-second retry-after. Fixed: scoped `DAILY_LIMIT_REACHED` to tiered user paths only; anon/login/register/billing_checkout 429s now pass through to DRF default. Caught during SSO regression investigation — would have killed acquisition on launch day.

**Backend hardening (Prompt C):** `PortalSessionView` return_url allowlist (ranktorole.app + localhost only, 400 on other URLs, +5 tests), production security headers gated on `DEBUG=False` (HSTS preload, SSL redirect, secure cookies, X-Frame DENY, strict referrer), tier integrity sweep passing all 5 invariants (read-only serializer, no frontend tier writes, CheckoutThrottle on billing, PRO_STATUSES alignment, webhook auth-only).

**Webhook E2E verification (real Stripe CLI forwarding).** Upgrade: checkout.session.completed + subscription.created/updated → AuditLog: inactive → active → incomplete → active. Cancel: subscription.deleted → active → canceled. Idempotent replay confirmed (3 duplicate .deleted events → no-ops). Free↔Pro UI state transitions verified in browser for both directions.

**Outstanding decision:** `billing_views.py` has `logger.warning` lines added to webhook except blocks during live debugging. Commit vs. revert deferred to next session's code review pass.

Test count: 226 → 233 (+7: 5 return_url allowlist tests, 1 throttle scoping test, 1 other).

Remaining launch blockers: secret rotation, EC2 deploy, production smoke test.

---

## April 21, 2026 | Global 429 daily-limit handler

`apiFetch` in `client.js` now dispatches a `daily-limit` CustomEvent (with `retryAfterSeconds` in detail) whenever the backend returns `DAILY_LIMIT_REACHED`. `AppShell` in `App.jsx` listens for this event and renders `<UpgradeModal variant="wait" />` globally. Removed duplicate local 429 handling from `useResumeMachine` (`handleGenerateDraft` and `handleChatSend` catch blocks), cleaned up dead `DAILY_LIMIT_HIT`/`DAILY_LIMIT_DISMISS` reducer cases and state fields, and removed the now-dead local `<UpgradeModal>` from `ResumeBuilder.jsx`. Backend unchanged.

---

## April 21, 2026 | Contract Fix — ResumeChatView 409 on is_finalized

`POST /api/v1/resumes/{id}/chat/` now returns 409 with `{"error": "Resume is finalized. Reopen it to continue editing."}` when `is_finalized=True`. Previously the endpoint allowed chat turns on finalized resumes, contradicting DATA_CONTRACT. Gate short-circuits before any Claude call. Test renamed from `test_finalized_resume_chat_still_works` to `test_finalized_resume_chat_returns_409`. DATA_CONTRACT.md and TASKS.md updated to reflect the enforced contract.

---

## April 21, 2026 | Session 14 | Recon Rebuild — Form-Driven Brainstorm

**Status:** ✅ Complete

### Summary

Replaced the SEARCH → RESULTS → DETAIL three-phase Recon UI with a single form-driven brainstorm endpoint modeled on RankToRole's intake pattern. Profile-decoupled by design: the form body is the sole source of signal. One best-match card with full O\*NET detail + Haiku reasoning, plus up to 2 slim "also consider" runner-up cards.

### Decisions

- **Profile-decoupled.** `user.profile_context` is never read by `recon_app`. First-time users can brainstorm from day one.
- **Ephemeral.** No model, no migration. Pin/save deferred post-launch — capstone CRUD-model scope stays at Resume + Contact.
- **New `recon_app` Django app.** Clean boundary. Reuses MOS resolver, global ceiling, and typed Haiku caller from `onet_app`.
- **Baseline-grounded Haiku.** Any `onet_code` Haiku returns that isn't in the O\*NET baseline is discarded, preventing code hallucination.
- **Throttle renamed.** `user_recon_enrich` → `user_recon_brainstorm`. Every active user's daily counter resets on deploy (acceptable at launch).
- **Degraded fallback.** On Haiku failure: strongest O\*NET crosswalk, no reasoning, `degraded: true`, HTTP 200.
- **Design-system debt noted.** `CareerRecon.jsx` inlines its page-header structure (breadcrumb + title) instead of using the shared `<PageHeader>` component. This was done during visual polish to apply a muted breadcrumb color, then reverted to match other pages but the inline structure stayed. Functionally identical to other pages but decoupled at the source level. Consolidate post-launch if `<PageHeader>` gains a color/variant prop.

### Backend Changes

| File                               | Action   | Detail                                                                  |
| ---------------------------------- | -------- | ----------------------------------------------------------------------- |
| `recon_app/`                       | Created  | New app with views, services, serializers, schemas, tests               |
| `onet_app/views.py`                | Pruned   | Deleted all view classes; kept utility helpers                          |
| `onet_app/urls.py`                 | Emptied  | No more endpoints                                                       |
| `onet_app/cache_utils.py`          | Deleted  | All consumers removed                                                   |
| `onet_app/recon_enrich_service.py` | Pruned   | Deleted enrich_career, \_build_enrichment_prompt, \_profile_fingerprint |
| `onet_app/schemas.py`              | Deleted  | CareerEnrichment no longer used                                         |
| `onet_app/tests.py`                | Pruned   | Kept MOS resolver and ceiling tests only                                |
| `onet_app/tests_cache.py`          | Deleted  | All three cache test classes removed                                    |
| `config/urls.py`                   | Modified | Removed onet_app include, kept recon_app                                |
| `config/settings.py`               | Modified | INSTALLED_APPS += recon_app, throttle scope renamed                     |
| `translate_app/throttles.py`       | Modified | `ReconEnrichThrottle.scope` → `user_recon_brainstorm`                   |

### Frontend Changes

| File                    | Action    | Detail                                  |
| ----------------------- | --------- | --------------------------------------- |
| `api/recon.js`          | Created   | `submitBrainstorm()`                    |
| `api/onet.js`           | Deleted   | Consumers gone                          |
| `pages/CareerRecon.jsx` | Rewritten | Single-form intake; tactical dark theme |

### Visual Polish (Prompts D–F)

After the initial Prompt B shipped, three follow-up prompts tightened the UI:

- **Prompt D** — removed duplicate hero/headline stack; demoted in-card title to a tagline; fixed garbled `(optional)` labels (parent uppercase transform was cascading onto span — fixed by matching ForgeSetup's `normal-case tracking-normal` pattern); eliminated floating-card pattern in favor of single card with clear boundary.
- **Prompt E** — restored green breadcrumb (`text-secondary`) to match Dashboard and other pages after Prompt D muted it (decision flipped after seeing it in context); fixed tagline to use `font-headline uppercase` to match app's headline treatment.
- **Prompt F** — matched page container and card classes to Dashboard exactly (`max-w-4xl mx-auto px-4 py-6 space-y-6` outer; `bg-surface-container p-5` card — no border, no rounded, no shadow) so `/recon` and `/dashboard` read as siblings.

### Test Count

| Stage                      | Count |
| -------------------------- | ----- |
| Pre-rebuild (baseline)     | 241   |
| After Prompt A (new tests) | 257   |
| After Prompt C (deletions) | 226   |

The drop from 257 → 226 is expected: 23 tests deleted from `onet_app/tests.py` (OnetSearchView × 3, OnetMilitarySearchView × 6, OnetCareerDetailView × 5, ReconEnrichView × 7, enrich cache × 2) + 8 tests deleted from `onet_app/tests_cache.py` = 31 deleted, 1 rewritten (`test_global_ceiling_returns_none` now tests `_check_and_increment_global_ceiling` directly). Net: −31.

### Post-launch backlog

1. Pin / Save model (deferred — new CRUD model post-launch decision)
2. Form auto-save to localStorage (opt-in only if users request it)
3. "Explore similar" button on also_consider cards (re-submit with that field pre-filled)

---

## April 20, 2026 (evening) | Tailoring v2: authority rebalance + per-role identity

**Status:** ✅ Shipped.

v1 shipped in the morning pushed test count 198 → 204 and added
TAILORING RULES alongside the 8 preservation rules. Smoke test against
Brandon's PSYOP resume + Unstructured Fort Bragg JD showed a specific
failure: ATS FIT ASSESSMENT was working well (JD vocabulary pulled
through correctly, real gaps named, specific question) but bullet-level
tailoring was near-zero. The preservation rules structurally outweighed
the tailoring rules — Claude interpreted "preserve every concrete fact"
as "preserve every sentence."

v2 rebalances in three substantive ways:

1. **Authority gradient inverted.** REWRITE is now the primary task;
   PRESERVATION is the constraint. Same rules; different framing. The
   prompt now explicitly calls a near-identical bullet a FAILED rewrite.

2. **Per-role identity model (P3).** Identity markers (PSYOP, SIGINT,
   Ukraine, ION, COR, etc.) must appear at least ONCE per role — in
   the org field, summary, or at least one bullet. Individual bullets
   can reframe in JD vocabulary without repeating the marker. This
   gives tailoring real room to operate without erasing career
   identity. Safer for cross-JD use (non-defense JDs no longer force
   PSYOP into every bullet of a defense role).

3. **R3 three-case rule.** Word-swap-on-match (required), reframe-
   accurate-activity-in-JD-vocabulary (required), fabricate-skill-not-
   in-source (forbidden). v1 conflated the first two with the third.

4. **Three demonstrated transformations** (Example 1/2/3) embedded in
   the prompt with Source / JD priorities / Tailored / What changed
   commentary. Sonnet 4 does substantially better style transfer with
   demonstrated patterns than with rule text alone.

The grounding validator remains untouched and remains the safety net.
Expected flag rate under v2: 10–25% of bullets on a well-grounded
source. If the rate climbs above ~40%, the rewrite rules are pulling
past the preservation line and need tightening.

Test count: 204 → 210 (6 new tests; 2 existing tests renamed or
language-updated).

---

## April 20, 2026 | JD Tailoring + ATS Assessment

**Status:** ✅ Shipped.

Two coupled prompt changes on top of the existing honesty stack:

- Added TAILORING RULES (T1–T5) to `_SYSTEM_PROMPT`, sitting alongside
  the 8 SOURCE PRESERVATION rules. Explicit instructions to analyse JD
  priorities first, reframe bullets through that lens, mirror JD
  vocabulary where factually accurate, reorder within-role bullets to
  lead with the JD-relevant accomplishment. Bullet count per role is
  still preserved (honesty).
- Restructured `call_claude_draft` user_message into a two-stage
  chain-of-thought: Stage 1 silent JD analysis, Stage 2 tailored
  translation through that lens. JD now appears before military
  background in the prompt.
- Changed the `clarifying_question` field's content contract — it now
  carries a structured ATS FIT ASSESSMENT (Strong matches / Gaps /
  Risk) followed by exactly ONE targeted question. No schema change;
  the field is still `str`.
- Frontend: added `whitespace-pre-wrap` to chat bubbles so the
  multi-line ATS assessment renders correctly. No reducer, hook, or
  API changes.

The grounding validator and flag-gated UX are the safety net. Pushing
the tailoring harder with defensive rules still holding means any
overreach (fabricated metric, scope inflation) surfaces as a bullet
flag for the user to verify or reject. Pressure-test flag rate on real
resumes; adjust if the rate creeps above ~20% of bullets.

Test count: 198 → 204 passing. +6 tests for new prompt sections.

---

## April 6, 2026 | Sessions 01 + 02 | Phase 1 → Phase 3 Complete

### Session 01 — Phase 1: Project Setup & Claude Code Configuration

**Duration:** Morning session | **Status:** ✅ Complete

**Stack Confirmed**

- Frontend: React 18 + Vite + Tailwind CSS + React Router DOM
- Backend: Django REST Framework, Python 3.12
- Database: PostgreSQL 16 (named volume)
- AI: Claude API (claude-sonnet-4-20250514)
- Auth: JWT via SimpleJWT + Google OAuth 2.0
- Public API: O\*NET Web Services (no key)
- Infrastructure: Docker Compose + Nginx
- Deployment: AWS EC2

**Architecture Decisions**

- Hybrid dev setup: Vite on host (HMR enabled), backend/db in Docker
- Vite proxies /api/ to localhost:8000 in dev
- Production: npm run build → dist/ → Nginx serves static + proxies API
- runserver in dev, gunicorn in production
- Named postgres volume (fixes BridgeBoard data loss on docker compose down)
- All API calls use relative paths — never hardcoded hosts

**Feature Decisions**

- User pastes job description manually — no job search API
- 2 CRUD models: Resume + Contact
- Google OAuth satisfies secret key requirement
- O\*NET satisfies public API requirement
- UUIDs on all models
- Lazy loading on frontend components

**Security Decisions**

- JWT access token: 15 min expiry, stored in memory only
- JWT refresh token: 7 days, httpOnly cookie
- CORS whitelist frontend URL only
- DB port never exposed externally
- No PII in server logs
- IAM instance role on EC2 (no hardcoded AWS credentials)

**Issues Encountered & Resolved**

| Issue                               | Resolution                     |
| ----------------------------------- | ------------------------------ |
| .gitignore corruption               | Fixed manually, recommitted    |
| zsh treating ! as history expansion | Run commands one at a time     |
| zsh treating # as commands          | Don't paste inline comments    |
| Git not initialized                 | ran git init                   |
| GitHub repo not found on first push | Created repo on github.com/new |

---

### Session 02 — Phases 2 + 3: Context Window Management + Full Stack Build

**Duration:** Afternoon/evening session | **Status:** ✅ Complete

**Phase 2 — Context Window Management**

Four-layer context architecture keeps every Claude API call under 5,000 tokens:

| Layer | Content                                   | Budget         | Policy                 |
| ----- | ----------------------------------------- | -------------- | ---------------------- |
| 1     | System prompt                             | ~400 tokens    | Static — never changes |
| 2     | Session anchor (compressed JD + resume)   | ~700 tokens    | Set once, always kept  |
| 3     | Decisions log (approved/rejected bullets) | ~100/bullet    | Never pruned           |
| 4     | Rolling chat window                       | ≤ 2,000 tokens | Oldest pruned first    |

Key classes: `DecisionsLog`, `RollingChatWindow`, `compress_session_anchor()`, `build_messages()`

**Phase 3 — Full Stack Build via Subagent Orchestration**

| Agent           | Files Created | Time     | Outcome                                    |
| --------------- | ------------- | -------- | ------------------------------------------ |
| scaffold-agent  | 45            | 2m 5s    | Django project + Vite scaffold             |
| models-agent    | 12            | 3m 3s    | All models, serializers, migrations        |
| auth-agent      | 8             | ~4m      | JWT + Google OAuth, 6 endpoints            |
| translate-agent | 7             | ~3m      | context.py, services.py, 18 tests          |
| auth-fix-agent  | 2             | ~1m      | Hybrid JWT — memory + httpOnly cookie      |
| frontend-agent  | 15            | 2m 42s   | React Router, all pages, components        |
| deploy-agent    | 3             | 46s      | docker-compose.yml, Dockerfile, nginx.conf |
| **Total**       | **92**        | **~17m** | **Full stack built**                       |

**Stack Verification**

| Check                       | Result                       |
| --------------------------- | ---------------------------- |
| docker compose up --build   | ✅ All 4 services started    |
| 48 migrations applied       | ✅ All OK                    |
| POST /api/v1/auth/register/ | ✅ UUID + JWT returned       |
| POST /api/v1/auth/login/    | ✅ Tokens issued             |
| Frontend loads at localhost | ✅ React app served by Nginx |
| API routing via Nginx       | ✅ /api/ proxied to backend  |

**Issues Encountered & Resolved**

| Issue                            | Resolution                                                             |
| -------------------------------- | ---------------------------------------------------------------------- |
| Backend started before DB ready  | Added healthcheck + depends_on: service_healthy                        |
| Nginx serving default page       | root directive pointed to /html not /html/dist                         |
| WSL2 bind mount stale cache      | docker compose down && up --build                                      |
| registerRequest missing username | Agent fix — added username field to API call and form                  |
| localStorage JWT (security)      | auth-fix-agent rewrote to hybrid pattern                               |
| Docker tests failing in agents   | Expected — no containers at build time, syntax validated via ast.parse |

---

## April 6, 2026 | Session 03 | Feature Design — PDF Flow & Intelligent Refinement Loop

**Status:** ✅ Design complete — ready for implementation

### Context

Moved beyond the original single-shot translation model. Redesigned the core product flow to eliminate the LLM as a middleman and deliver a collaborative, cost-efficient resume tailoring experience.

**Trigger:** Reviewed Calvin's actual resume PDF (Google_Ops_Resume_Calvin_Joewono.pdf). Confirmed PDF is text-native (not scanned) — PyMuPDF will extract cleanly with no OCR needed. Two-column skills section will extract sequentially, which is fine for LLM consumption.

### Documentation Updated (end of Session 03)

The following files were revised to reflect the new PDF flow architecture:

- CLAUDE.md — updated LLM integration, URL map, Pydantic schema, cost reference
- ARCHITECTURE.md — rewrote product flow, Claude integration pattern, Resume model, frontend state machine
- DATA_CONTRACT.md — full rewrite: 4 endpoint contracts (upload, draft, chat, finalize)
- TASKS.md — old single-shot tasks marked complete, new 7-step sprint added, EC2 pushed to Phase 5

All docs now in sync with Session 03 design. Ready for implementation.

---

### New Product Flow

```
1. Upload PDF         → extract text, create Resume record, return resume_id
2. Paste JD           → single LLM call returns draft + 2-3 clarifying questions
3. Answer questions   → stateless refinement turns (history passed from frontend)
4. Approve & Finalize → user edits bullets inline, confirms, is_finalized = True
```

**Key design principle:** LLM never sees the raw PDF or JD again after call 1. All subsequent turns use the compressed session anchor (~350 tokens) + rolling frontend history. This keeps the refinement loop at ~1,250 input tokens per turn.

---

### Cost Analysis (claude-sonnet-4-20250514 — $3 input / $15 output per 1M tokens)

| Call                                  | Input tokens | Output tokens | Cost               |
| ------------------------------------- | ------------ | ------------- | ------------------ |
| Call 1 — PDF + JD → draft + questions | ~2,300       | ~600          | ~$0.016            |
| Each refinement turn                  | ~1,250       | ~600          | ~$0.013            |
| Full session (call 1 + 3 turns)       | —            | —             | **~$0.055**        |
| With prompt caching enabled           | —            | —             | **~$0.025–$0.035** |

At 1,000 sessions/month: **$25–$55/month**. Negligible at this scale.

---

### Architecture Decisions

**Pydantic schema expansion** — single JSON blob covers both UI panes on every call:

```python
class MilitaryTranslation(BaseModel):
    civilian_title: str
    summary: str
    bullets: list[str]
    clarifying_questions: list[str]  # 2-3 on draft call, [] on refinement turns
    assistant_reply: str             # "" on draft call, populated on chat turns
```

**Stateless refinement loop** — chat history passed from frontend on each request. Eliminates `chat_history` DB column. Justified by session length (3-4 turns max). Backend reconstructs context from `session_anchor` (DB) + `history` (request body) on every turn.

> **Superseded by Session 05:** chat history moved into the DB; the backend owns
> it and loads it on every chat turn. See the Session 05 entry below.

**Frontend state machine:**

```
IDLE → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE
```

Single `status` state variable drives all conditional renders. Split-pane layout: draft on left, chat on right.

---

### Schema Changes

**Resume model** — one migration, do it now before Phase 1 code:

| Field             | Change                                                    |
| ----------------- | --------------------------------------------------------- |
| `job_description` | Add `blank=True` — upload creates record before JD exists |
| `civilian_title`  | Add `blank=True` — same reason                            |
| `summary`         | Add `blank=True` — same reason                            |
| `is_finalized`    | **New** — `BooleanField(default=False)`                   |

**New dependency:** `pymupdf==1.24.11` → `requirements.txt` + Docker rebuild

---

### New URL Map

| Method | Endpoint                         | Phase    | Purpose                                     |
| ------ | -------------------------------- | -------- | ------------------------------------------- |
| POST   | `/api/v1/resumes/upload/`        | 1        | PDF → military_text, returns resume_id      |
| POST   | `/api/v1/resumes/{id}/draft/`    | 2        | JD → draft + questions, sets session_anchor |
| POST   | `/api/v1/resumes/{id}/chat/`     | 3        | message+history → updated draft + reply     |
| PATCH  | `/api/v1/resumes/{id}/finalize/` | 4        | final edits → is_finalized=True             |
| GET    | `/api/v1/resumes/`               | existing | dashboard list                              |
| GET    | `/api/v1/resumes/{id}/`          | existing | retrieve single                             |
| DELETE | `/api/v1/resumes/{id}/`          | existing | delete                                      |

---

### Implementation Order (next session)

1. Migration — `is_finalized`, `blank=True` on partial fields
2. `requirements.txt` — add `pymupdf==1.24.11`, Docker rebuild
3. `POST /api/v1/resumes/upload/` — PyMuPDF extraction, create Resume record
4. Update serializers — handle partial Resume state (fields empty until draft call)
5. `POST /api/v1/resumes/{id}/draft/` — JD input, double-duty LLM call, save anchor
6. `POST /api/v1/resumes/{id}/chat/` — stateless refinement, update draft fields
7. `PATCH /api/v1/resumes/{id}/finalize/` — save final state, flip is_finalized
8. Frontend — replace Translator page with split-pane + status machine + file dropzone
9. Smoke test full flow end-to-end

---

## April 7, 2026 | Session 04 | Phase 4 Complete — PDF Builder Flow

**Status:** ✅ Complete

### Step 0 — Code Review & Bug Fixes

Six pre-existing bugs identified and fixed before any new code:

| Fix | File             | Issue                                                    |
| --- | ---------------- | -------------------------------------------------------- |
| 1   | contacts.js      | PUT → PATCH on updateContact                             |
| 2   | views.py         | ResumeDetailView missing delete() method                 |
| 3   | Contacts.jsx     | phone field not in Contact model — removed from frontend |
| 4   | TASKS.md         | All Phase 3 tasks marked [x]                             |
| 5   | models.py        | is_finalized BooleanField added + migration 0002 applied |
| 6   | requirements.txt | pymupdf==1.24.11 added                                   |

pytest: 38/43 passing (5 pre-existing rate-limiter failures)

### Rate Limiter Fix

LoginRateThrottle set directly on view class — global settings override
had no effect. Fixed via monkeypatch.setattr + cache.clear() in autouse
fixture. Result: 43/43 passing. Committed.

### Phase 4A — Backend (4 new endpoints)

Built by backend agent, all endpoints verified via pytest:

| Endpoint                             | View               | Notes                                                      |
| ------------------------------------ | ------------------ | ---------------------------------------------------------- |
| POST /api/v1/resumes/upload/         | ResumeUploadView   | PyMuPDF extraction, MIME validation                        |
| POST /api/v1/resumes/{id}/draft/     | ResumeDraftView    | DraftResponse Pydantic schema, session anchor compression  |
| POST /api/v1/resumes/{id}/chat/      | ResumeChatView     | Stateless — history passed from frontend, 409 if finalized |
| PATCH /api/v1/resumes/{id}/finalize/ | ResumeFinalizeView | Sets is_finalized=True, 409 if already finalized           |

pytest: 38/43 → baseline held (pre-existing failures only)

### Phase 4B — Frontend (6 new files, 2 modified)

Built via 7-task subagent execution with spec review + code review per task.

**Files created:**

- frontend/src/api/resumes.js
- frontend/src/pages/ResumeBuilder.jsx
- frontend/src/components/SplitPane.jsx
- frontend/src/components/DraftPane.jsx
- frontend/src/components/ChatPane.jsx
- frontend/src/components/UploadForm.jsx

**Files modified:**

- frontend/src/App.jsx — /resume-builder route added
- frontend/src/pages/Dashboard.jsx — "Open Builder" button + is_finalized badge

**Key fixes caught during code review:**

- CHAT_FAILED action added (orphaned optimistic message on failure)
- DRAFT_FAILED action added (user stuck in DRAFTING with no retry path)
- Dead err.message.includes("409") string check removed
- FinalizingEditor uses fresh-mount pattern (not useEffect sync)
- MIME check uses file.type not extension
- FormData Content-Type fix in client.js (instanceof FormData → delete header)

**State machine (useReducer):**
IDLE → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE

### Smoke Test Results

| Step                                    | Result | Notes                                     |
| --------------------------------------- | ------ | ----------------------------------------- |
| 1. Dashboard shows both buttons         | ✅     | Stale Docker volume required purge        |
| 2. /resume-builder loads                | ✅     | ResumeBuilder-BPmMJy3m.js chunk confirmed |
| 3. PDF upload → 201                     | ✅     | Content-Type fix resolved multipart issue |
| 4. Generate Draft → split pane          | ✅     | Blocked by zero API credits — resolved    |
| 5. Clarifying questions as chat bubbles | ✅     | 3 targeted questions rendered             |
| 6. Chat reply → draft updates           | ✅     | Stateless refinement working              |
| 7/8. Finalize flow                      | ✅     | Editable fields → DONE state              |
| 9. Dashboard Finalized badge            | ✅     | Green pill renders correctly              |

**Issues encountered:**

| Issue                                       | Resolution                                                        |
| ------------------------------------------- | ----------------------------------------------------------------- |
| Stale frontend_dist volume                  | docker volume rm + rebuild                                        |
| Content-Type: undefined not removing header | instanceof FormData → delete headers["Content-Type"] in client.js |
| Zero API credits                            | Added credits + rotated to funded workspace key                   |
| ANTHROPIC_API_KEY not reloading             | docker compose up -d to pick up new .env                          |

### Output Quality

Draft call for military background → "Technical Program Manager - Analytics & Data Solutions"
with quantified bullets and targeted clarifying questions about BI tooling, SQL,
and marketing analytics. Translation quality confirmed strong end-to-end.

### Known Issues (non-blocking)

- DraftPane rendering more bullets than 3-5 specified in DATA_CONTRACT — prompt
  engineering issue in call_claude_draft, not a UI bug. Follow-up fix needed.

---

## April 9, 2026 | Session 05 | UI/UX Overhaul + Phase D Complete

**Status:** ✅ Complete

### What Was Built

#### Backend (Phase A)

- Resume model: added roles[], chat_history[], ai_initial_draft fields (migration 0003)
- Pydantic schema: MilitaryTranslation updated — RoleEntry(title, org, dates, bullets[])
- Prompt engineering: preserves role structure from PDF, rewrites bullets only
- Single clarifying question per draft (JD-specific, high-impact)
- /chat/ endpoint: loads chat_history from DB — frontend no longer sends history
- /finalize/ endpoint: accepts roles[] + civilian_title + summary
- 75 tests passing throughout

#### Frontend (Phase B + C + D)

- DraftPane: full rewrite — role cards in REVIEWING, accordion bullet editor in FINALIZING
- Live redline diff (diffWords LCS utility) vs ai_initial_draft per bullet
- AI suggestion chips — Accept/Dismiss, manual edits never clobbered
- Chat active in both REVIEWING and FINALIZING phases
- SplitPane: sticky right pane (100vh), left scrolls independently
- Export PDF via jsPDF — role-grouped clean format, downloads to local machine
- Dashboard: Finalized/In Progress/Not Started badges, Continue + Edit & Export re-entry
- Resume re-entry: ?id=&mode=continue/edit loads from DB on mount
- Translator page hidden from nav (route preserved)

### Issues Encountered & Resolved

| Issue                             | Resolution                                                              |
| --------------------------------- | ----------------------------------------------------------------------- |
| draft.roles.map() crash on render | Null guards added across DraftPane + ChatPane                           |
| Edit & Export loading blank IDLE  | resumeId: resume.id fix in RESUME_LOADED                                |
| Sticky chat pane not working      | SplitPane overflow:hidden + height:100% on right pane                   |
| Export PDF button missing         | Rewrote exportPDF() with jsPDF, button at top-right of FinalizingEditor |
| Single question schema            | clarifying_questions: list[str] → clarifying_question: str              |
| Stale build cache                 | docker compose stop + rebuild cleared crash                             |

---

## April 10, 2026 | Post-Session 05 Fixes

**Status:** ✅ Complete

### Critical Fixes (Anthropic API 529 Overloaded Recovery)

Backend resilience improved via live testing under actual Anthropic API load. All issues resolved and verified.

#### services.py

- **Fix 1:** call_claude_chat() missing return statement — chat endpoint returned 500 instead of 200
- **Fix 2:** Consecutive user turns now properly formatted — anchor folded into first history turn when history starts with user role, preventing Anthropic "role must alternate" rejection
- **Fix 3:** Broadened exception handling in \_call_claude_typed to catch non-APIError exceptions

#### views.py

- **Fix 4:** Moved user message append to after successful Claude call — prevents duplicate messages on failed requests
- **Fix 5:** Added 10MB file size check in ResumeUploadView
- **Fix 6:** Added PDF magic bytes validation (%PDF- header check) before PyMuPDF extraction — prevents spoofed MIME types

#### tests.py

- **Fix 7:** test_file_too_large_returns_400 — validates file size enforcement
- **Fix 8:** test_spoofed_mime_type_returns_400 — validates magic bytes check

### Verification

- **Pytest:** 77/77 tests passing (all backend test suite)
- **Live smoke test:** Two consecutive chat turns succeeded:
  - Turn 1: "Strengthen the first bullet" → returned roles[] + assistant_reply
  - Turn 2: "Make summary more concise" → returned updated roles[] + assistant_reply
- **API recovery:** After initial 529, retry loop succeeded on first attempt once Anthropic API recovered

### Commit

- **Hash:** d6527c9
- **Files:** backend/translate_app/services.py, views.py, tests.py
- **Message:** "fix: chat consecutive user turns, duplicate message, PDF security checks"

---

## April 10, 2026 | Session 06 | API Layer Refactor + Service Layer Cleanup

**Status:** ✅ Complete

### API Client Refactor (Frontend)

Centralized error handling across all frontend API modules:

- **APIError class** added to `client.js` — carries `status`, `message`, and `data` fields
- **`handleResponse()` helper** — single place that checks `res.ok`, parses JSON, and throws `APIError` on failure
- `apiFetch()` now returns parsed data directly and throws `APIError` instead of raw `Response`
- **Eliminated manual error handling** from `resumes.js`, `auth.js`, `contacts.js`, and `translations.js` — all four modules now rely on the centralized helper

Previously each module had its own `if (!res.ok)` blocks with inconsistent error extraction. All error paths now flow through one code path.

### PDF Export Utility

- Extracted `exportPDF()` out of `DraftPane.jsx` into standalone `frontend/src/utils/pdfExport.js`
- `DraftPane.jsx` now imports from the utility module — no behavior change

### Backend Service Layer (services.py)

- **`ChatResult` dataclass** added to `services.py` — encapsulates `(translation, updated_history)` return tuple
- `call_claude_chat()` now returns a `ChatResult` instead of a bare tuple
- `ResumeChatView` updated to consume `ChatResult` attributes
- Test helper `make_chat_result()` added; 4 `TestResumeChatView` tests updated to mock `ChatResult` return type

### Verification

- pytest: **77/77 passing** throughout refactoring
- No regressions — backend and frontend changes are independent

---

## April 11, 2026 | Session 07 | SPA Architecture + Component Decomposition

**Status:** ✅ Complete

### Part A — SPA Shell Refactor

Replaced per-page NavBar rendering with a persistent `AppShell` pattern:

| Change                       | Detail                                                                                                                           |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `AppShell` component         | Always mounts NavBar once; pages are shown/hidden via CSS (`hidden` class), not unmounted                                        |
| `ResumeContext`              | New context file (`frontend/src/context/ResumeContext.jsx`) wires up shared resume state                                         |
| `fullscreen` state           | Lives in `AppShell`, passed as `setFullscreen` prop to `ResumeBuilder` — AppShell applies `overflow-hidden` on split-pane phases |
| `PageHeader` component       | Shared header (`frontend/src/components/PageHeader.jsx`) — renders label badge, bold headline, optional action slot              |
| Dashboard refactor           | Imports `PageHeader`, removed NavBar                                                                                             |
| Contacts refactor            | Imports `PageHeader`, removed NavBar                                                                                             |
| ResumeBuilder refactor       | Now accepts `setFullscreen` prop; calls `setFullscreen(true)` on split phases, `false` otherwise                                 |
| `ProtectedRoute.jsx` deleted | Dead code — AppShell's auth guard replaces it entirely                                                                           |
| Catch-all redirect           | Unknown paths redirect to `/dashboard` instead of blank screen                                                                   |

**Benefit:** NavBar no longer remounts on every route change. SplitPane fullscreen triggers no layout flash.

### Part B — Frontend Component Decomposition

#### useResumeMachine custom hook

Extracted the entire state machine out of `ResumeBuilder.jsx` into `frontend/src/hooks/useResumeMachine.js`:

| Moved to hook         | Detail                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------ |
| `initialState`        | 9-field initial state object                                                               |
| `reducer`             | 18 action cases (IDLE → LOADING → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE)     |
| `useEffect` re-entry  | Reads `?id=&mode=` search params on mount, loads resume from DB via `getResume()`          |
| `handleGenerateDraft` | `useCallback`-wrapped, calls `generateDraft()` API                                         |
| `handleChatSend`      | `useCallback`-wrapped, calls `sendChatMessage()`, dispatches optimistic + received actions |

Hook returns `{ state, dispatch, handleGenerateDraft, handleChatSend }`. `ResumeBuilder.jsx` reduced to JSX-only (1 hook call, no logic).

#### DraftPane component split

Replaced flat `frontend/src/components/DraftPane.jsx` with a directory:

| File                             | Responsibility                                                                                                      |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `DraftPane/DiffView.jsx`         | Word-level LCS diff, renders added/removed spans                                                                    |
| `DraftPane/BulletEditor.jsx`     | Accordion bullet editor with AI suggestion chip (Accept/Dismiss)                                                    |
| `DraftPane/FinalizingEditor.jsx` | Full editing UI — title, summary, role bullets, sticky confirm button                                               |
| `DraftPane/index.jsx`            | Main DraftPane wrapper — REVIEWING (read-only cards), FINALIZING (delegates to FinalizingEditor), DONE (export CTA) |

All existing consumers (`ResumeBuilder.jsx`, etc.) continue importing `../components/DraftPane` unchanged — Vite resolves directory imports to `index.jsx` automatically.

### Verification

- pytest: **77/77 passing** — no backend regressions
- Vite production build: **441 modules**, 0 import errors
- Structural checks: no `useReducer`/`reducer`/`initialState` remaining in `ResumeBuilder.jsx`, only one component function exported from `DraftPane/index.jsx`

---

## April 12, 2026 | Task 6 | Tiered Throttle System

**Status:** ✅ Complete

Implemented tiered throttle system: `User.tier` field (free/pro), `TieredThrottle` base class, 5 throttle subclasses in `translate_app/throttles.py`, `TIERED_THROTTLE_RATES` settings, 20 new tests (64 → 84 total).

Cache key includes tier so upgrade/downgrade takes effect immediately without waiting for cache expiry.

---

## April 13, 2026 | HTTPS/SSL + Production Deployment Prep

**Status:** ✅ Complete

### Changes Made

- **settings.py:** Fixed HSTS bug (`0 if DEBUG else 0` → `0 if DEBUG else 31536000`). Added `CSRF_TRUSTED_ORIGINS` setting (required by Django 4.2+ behind HTTPS proxy).
- **nginx/default.conf:** Rewritten for SSL termination — port 80 serves ACME challenge + redirects to HTTPS, port 443 serves frontend + proxies API with full security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy).
- **docker-compose.yml:** Added port 443 to Nginx. Added `/etc/letsencrypt` and `/var/lib/letsencrypt` read-only volume mounts to Nginx container.
- **.env.example:** Updated with all production env vars including `CSRF_TRUSTED_ORIGINS`, production override comments.
- **SECURITY.md, ARCHITECTURE.md, CLAUDE.md:** Updated with SSL/HTTPS deployment details.

### Dev Workflow Impact

None. Dev still uses Vite on host + backend in Docker with runserver. Nginx is never started in dev. All new settings gated on `DEBUG` or read from `.env` with safe defaults.

### Manual Steps Required (not in repo)

1. DNS: Point `ranktorole.app` and `www.ranktorole.app` A records to EC2 public IP
2. EC2 security group: Confirm ports 80/443 open, 22 from your IP only, no 8000/5432
3. Install Docker on EC2 if not already installed
4. Install Certbot on EC2: `sudo apt install certbot`
5. Create production `.env` on EC2 with `DEBUG=False`, rotated `SECRET_KEY`, real DB password, production `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `GOOGLE_OAUTH_REDIRECT_URI=https://ranktorole.app/auth/google/callback`
6. Google Cloud Console: Add `https://ranktorole.app/auth/google/callback` as authorized redirect URI
7. Run Certbot to obtain cert
8. Start Docker Compose, run migrations, verify end-to-end

---

## April 13, 2026 | Security Hardening — Input Validation, Rate Limiting, Code Quality

**Status:** ✅ Complete — 84 → 97 tests passing

### Category 1 — Input Validation

- **JD length (ResumeDraftView):** Explicit 10-char minimum and 15,000-char maximum enforced in view (belt-and-suspenders over serializer's min_length).
- **Chat message cap (ResumeChatView):** 2,000-char maximum added to prevent context window abuse.
- **Finalize payload (FinalizeInputSerializer + RoleEntrySerializer):** Added max_length on all fields — civilian_title (200), summary (3,000), roles list (20 items), each role.title/org (200), dates (100), bullets list (10 items), each bullet (500 chars).
- **ContactSerializer:** Added max_length to all fields — name/company/role (200), email (254, RFC 5321), notes (5,000).

### Category 2 — Security

- **is_finalized gate on chat:** POST /chat/ now returns 409 if resume is already finalized, matching DATA_CONTRACT.
- **is_finalized gate on finalize:** PATCH /finalize/ now returns 409 if already finalized, matching DATA_CONTRACT.
- **RegisterThrottle:** New `AnonRateThrottle` subclass (scope=register, 5/hour) added to RegisterView.
- **Login error normalization:** LoginView always returns `{"error": "Invalid email or password."}` — prevents user enumeration.
- **Register error normalization:** RegisterView returns generic `{"error": "Registration failed."}` — prevents email enumeration.
- **HTML sanitization:** `strip_tags()` applied to all Claude-generated string fields in `_call_claude_typed` before returning — prevents stored XSS in PDF export or email contexts.
- **FinalizeThrottle / user_finalize:** Already present. CSP header: already in nginx. Token blacklist: already in INSTALLED_APPS.

### Category 3 — Code Quality

- **Dead code removed:** Unused `compress_session_anchor` import removed from views.py; unused `TranslationOutputSerializer` removed from serializers.py.
- **Type hints:** `Request` + `Response` type annotations added to all view methods.
- **Docstrings:** Comprehensive docstrings added to all services.py functions.
- **`get_user_resume()` helper:** Extracted repeated try/except Resume.objects.get() into a shared utility used by DraftView, ChatView, FinalizeView, DetailView.
- **`__str__` on User:** `User.__str__` returns `email (tier)` for admin readability.

### Tests Added (84 → 97)

- `test_jd_exactly_9_chars_returns_400`, `test_jd_too_long_returns_400`, `test_jd_at_minimum_length_returns_200`, `test_draft_on_existing_draft_is_idempotent`
- `test_chat_message_too_long_returns_400`, `test_finalized_resume_chat_returns_409`
- `test_double_finalize_returns_409` (was 200), finalize boundary tests (6 new)
- `test_register_throttle_returns_429`, `test_google_callback_invalid_state_returns_400`, `test_google_callback_missing_code_returns_400`

---

## April 13, 2026 | Session 10 | Career Recon — Standalone O\*NET Career Explorer

**Status:** ✅ Complete

### Summary

Built a standalone career exploration tool at `/recon` using O\*NET's My Next Move for
Veterans API. Users enter a MOS code and explore matching civilian careers with skills,
knowledge, technology, salary, and job outlook data — all at zero LLM cost.

### Backend Changes

| File                | Action   | Detail                                                    |
| ------------------- | -------- | --------------------------------------------------------- |
| `onet_app/views.py` | Modified | Added `OnetMilitarySearchView` and `OnetCareerDetailView` |
| `onet_app/urls.py`  | Modified | Added `/military/` and `/career/<onet_code>/` routes      |
| `onet_app/tests.py` | Created  | 11 tests covering search, detail, validation, auth        |

### Frontend Changes

| File                    | Action   | Detail                                                  |
| ----------------------- | -------- | ------------------------------------------------------- |
| `api/onet.js`           | Created  | API functions for military search and career detail     |
| `pages/CareerRecon.jsx` | Created  | Three-phase career explorer (SEARCH → RESULTS → DETAIL) |
| `App.jsx`               | Modified | Added `/recon` route and AppShell visibility            |
| `NavBar.jsx`            | Modified | Added "Recon" link (desktop + mobile)                   |

---

## April 13, 2026 | O\*NET v2 API Migration

**Status:** ✅ Complete

### Summary

Migrated all three O\*NET proxy views from the public `services.onetcenter.org/ws` endpoint to the authenticated v2 API at `api-v2.onetcenter.org`. Auth uses `X-API-Key` header sourced from `ONET_API_KEY` env var. No endpoint path changes — all routes and response shapes unchanged.

### Changes

| File                 | Action   | Detail                                                                           |
| -------------------- | -------- | -------------------------------------------------------------------------------- |
| `config/settings.py` | Modified | Added `ONET_API_KEY` from env                                                    |
| `onet_app/views.py`  | Modified | New base URL, shared `_onet_headers()` helper, all requests now send `X-API-Key` |
| `onet_app/tests.py`  | Modified | Added 3 tests verifying API key header is sent                                   |
| `.env.example`       | Modified | Added `ONET_API_KEY`                                                             |
| Docs                 | Modified | CLAUDE.md, ARCHITECTURE.md, SECURITY.md, PROJECTLOG.md updated                   |

### Follow-up: v2 Response Shape Fix

Fixed field name mismatches between v1 and v2 API responses:

- `military_matches.match` → `military_match` (top-level flat array)
- Overview `description` → `what_they_do` (v2 uses different field name)
- Skills/knowledge: v2 returns a list of categories with sub-`element` arrays (not `{"element": [...]}` dict)
- Technology: v2 returns list directly; category `title` is a plain string (not `{"name": "..."}`); examples use `title` key (not `name`)
- Outlook sub-endpoint: `outlook` → `job_outlook`
- Updated test mocks to use v2 field shapes
- Tests: 115/115 passing

---

## April 14, 2026 | Billing — Stripe Subscription (Free / Pro Tiers)

**Status:** ✅ Complete

### Summary

Wired up Stripe Checkout + Customer Portal to drive the existing `User.tier`
field. Webhooks flip tier on the server; the frontend only reads billing state.
PCI scope stays at SAQ A — card data is never seen or stored by our app.

### Backend Changes

| File                             | Action   | Detail                                                                                                                                                                                          |
| -------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `user_app/models.py`             | Modified | Added `stripe_customer_id`, `subscription_status` fields; added `SubscriptionAuditLog` immutable log model; added `resume_tailor_count` + `last_reset_date` daily counters                      |
| `user_app/billing_services.py`   | Created  | Stripe SDK wrapper — `get_or_create_customer`, `create_checkout_session`, `create_portal_session`, `verify_webhook`; idempotency keys on all create calls                                       |
| `user_app/billing_views.py`      | Created  | `CheckoutSessionView`, `PortalSessionView`, `BillingStatusView`, `StripeWebhookView`; `_STATUS_TO_TIER` map drives tier transitions; `select_for_update` + audit log under a single transaction |
| `user_app/billing_throttles.py`  | Created  | `CheckoutThrottle` (5/min) to defeat card-testing                                                                                                                                               |
| `user_app/billing_urls.py`       | Created  | `/api/v1/billing/{checkout,portal,status,webhook}/`                                                                                                                                             |
| `user_app/permissions.py`        | Created  | `IsProOrUnderLimit` (daily-reset counter) + `ChatTurnLimit` (permanent per-resume chat counter); `PRO_STATUSES = {'active', 'trialing', 'past_due'}`                                            |
| `user_app/serializers.py`        | Modified | `UserSerializer` exposes `subscription_status`, `resume_tailor_count`, `last_reset_date` (all read-only)                                                                                        |
| `config/urls.py`                 | Modified | Mounted `user_app.billing_urls` at `/api/v1/billing/`                                                                                                                                           |
| `config/settings.py`             | Modified | Added `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, `STRIPE_CHECKOUT_SUCCESS_URL`, `STRIPE_CHECKOUT_CANCEL_URL`, `FREE_TIER_DAILY_LIMITS`, `FREE_TIER_CHAT_LIMIT`            |
| `requirements.txt`               | Modified | Added `stripe==11.1.1`                                                                                                                                                                          |
| `user_app/tests/test_billing.py` | Created  | Checkout/portal/status/webhook coverage including signature verification failures, duplicate event replay, and status→tier transitions                                                          |

### Security Properties

- Webhook signature verified via `stripe.Webhook.construct_event` before any DB work
- Idempotency enforced by `stripe_event_id` unique constraint on `SubscriptionAuditLog` — replays return `{received: true, duplicate: true}`
- Audit log is append-only (no `updated_at`, ordered `-timestamp`) — every status transition is traceable for financial audit
- `stripe_customer_id` is the only Stripe reference persisted; no PAN/CVV anywhere in our system
- CSRF exempt on webhook only (required by Stripe); all other billing endpoints behind JWT

### Frontend

- `api/billing.js` added with `createCheckoutSession`, `createPortalSession`, `getBillingStatus`
- `UpgradeModal.jsx` added — triggered from builder when free-tier limits hit
- Builder flows read `BillingStatusView` output to render remaining daily quota

---

## April 15, 2026 | Pre-Deployment Audit

**Status:** ✅ Complete

### Summary

Final sweep before pointing DNS at the EC2 host. Focus: CVE patching, test
hygiene, migration sync, and production config verification. No functional
changes — everything in this session is infrastructure, dependencies, or docs.

### Dependency Upgrades (CVE-driven)

| Package                       | Before | After  | Reason                                      |
| ----------------------------- | ------ | ------ | ------------------------------------------- |
| Django                        | 4.2.16 | 4.2.30 | 22 CVEs patched (staying on 4.2.x LTS line) |
| djangorestframework-simplejwt | 5.3.1  | 5.5.1  | Signing-key handling fixes                  |
| requests                      | 2.32.3 | 2.33.0 | CVE-driven bump                             |
| cryptography                  | 46.0.6 | 46.0.7 | Transitive patch                            |

### Intentionally Pinned (Deferred)

| Package                | Current | Latest | Why deferred                                     |
| ---------------------- | ------- | ------ | ------------------------------------------------ |
| social-auth-app-django | 5.4.2   | 5.6.0  | 5.6.0 requires Django 5.1; we're on 4.2 LTS      |
| anthropic              | 0.40.0  | 0.94.x | Too many breaking changes to absorb pre-deadline |
| Vite / esbuild         | —       | —      | Dev-only vuln, no production exposure            |

### Model / Migration Changes

- `Resume.chat_turn_count` field added (migration `0005_resume_chat_turn_count`) — backs the per-resume chat quota enforced by `ChatTurnLimit`
- All migrations verified in sync between `models.py` and `migrations/`

### Test & Code Hygiene

- 132 backend tests passing (up from 115), zero warnings
- Unused imports cleaned from `views.py` and `serializers.py`
- Zero `console.log` calls remaining in the frontend bundle
- Root `backend/conftest.py` verified — `autouse` fixture globally patches `anthropic.Anthropic` with `MagicMock`, so no test ever hits the real API

### Deployment Repo Changes

- `settings.py` — HSTS value finalized (31,536,000s when `DEBUG=False`), `CSRF_TRUSTED_ORIGINS` wired through env
- `nginx/default.conf` — SSL termination + HTTP → HTTPS redirect confirmed
- `docker-compose.yml` — port 443 exposed, `/etc/letsencrypt` mounted read-only into Nginx
- `.env.example` — expanded to cover every production var (Stripe, ONET, Google OAuth, CSRF, CORS)
- `ARCHITECTURE.md`, `CLAUDE.md`, `DATA_CONTRACT.md`, `SECURITY.md`, `README.md` — all brought current; `AGENTS.md` annotated as historical

### Open Items (Manual, on EC2 Day-Of)

All covered in ARCHITECTURE.md § SSL / HTTPS. Summary:

1. DNS A records for `ranktorole.app` and `www.ranktorole.app` → EC2 public IP
2. Security group: ports 80/443 open to world; 22 from admin IP; no 8000 or 5432
3. `apt install docker.io docker-compose-plugin certbot`
4. Production `.env` on host with `DEBUG=False`, rotated `SECRET_KEY`, real DB password
5. `sudo certbot certonly --standalone -d ranktorole.app -d www.ranktorole.app`
6. Google Cloud Console — add `https://ranktorole.app/auth/google/callback` as authorized redirect
7. Stripe dashboard — live webhook endpoint pointed at `https://ranktorole.app/api/v1/billing/webhook/`, signing secret copied into `.env`
8. `0 */12 * * * certbot renew --quiet && docker compose exec nginx nginx -s reload` in crontab

---

## April 16, 2026 | Session 11 | Smoke-Test Fixes + Dev Override

**Status:** ✅ Complete

Post-launch smoke testing surfaced three issues fixed in this session:

- **`chat_turn_count` serializer fix** — the field was persisting correctly on the backend but not being returned to the frontend, so the chat-limit UI couldn't render the counter. Serializer updated to include the field in read responses.
- **CHAT_LIMIT_REACHED UI** — when a free-tier user hit the 10-turn per-resume chat limit, the backend returned 403 but the frontend surfaced only a generic error. Added a dedicated `CHAT_LIMIT_REACHED` state in `useResumeMachine` that renders an `UpgradeModal`-style prompt in `ChatPane`.
- **`docker-compose.override.yml`** — initial version checked in to support dev bind mount patterns without touching the production `docker-compose.yml`.

Test count: 132 → 135 passing.

---

## April 16, 2026 | Session 12 | Dev Experience + Orphan Handling

**Status:** ✅ Complete — six commits shipped.

| Commit                | Change                                                                                                                                                                                                                                                                                                                                         |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `b88be47`             | Dev bind mount finalized in `docker-compose.override.yml` — backend hot-reloads on host file changes, runserver picks up edits without rebuild                                                                                                                                                                                                 |
| `9d17feb`             | Reopen regression fix — clicking "Reopen Resume" now requires an explicit click action (no auto-reopen on Dashboard hover)                                                                                                                                                                                                                     |
| `4a8fd25` + `bec6a9a` | Tailor-limit `UpgradeModal` — when a free-tier user hits their 1/day resume tailor quota, the modal offers upgrade path. Fix in `bec6a9a` moved the tailor-limit flag from `UploadForm` local `useState` to `useResumeMachine` reducer state (see Learnings below)                                                                             |
| `5d8b820`             | **Orphans resumable** — pre-draft resumes (PDF uploaded but `roles=[]` AND `session_anchor=null`) are now detectable in `useResumeMachine`, routed to `UPLOADED` phase on re-entry, and displayed on Dashboard with a new `UPLOADED` badge (tertiary color, distinct from `IN PROGRESS`). Stats cards fold UPLOADED into the IN PROGRESS count |
| `11c30fc`             | Dashboard refresh trigger — `useResumeMachine`'s `useEffect` on phase now calls `refreshResumes()` on all three of UPLOADED, REVIEWING, and DONE (not just DONE). Previously, newly-uploaded orphans required a hard page refresh before appearing on the Dashboard. Also fixes a promo-banner flash on Dashboard re-entry                     |

### Learnings (worth preserving)

- **React lifecycle gotcha (fixed in `bec6a9a`):** when a reducer action triggers a phase transition that unmounts a component, any `setState` calls in that component's local `useState` hooks that fire afterward are silently discarded. Lift persistent-across-phase flags into reducer state, not component-local state.
- **Dashboard refresh trigger scope:** any phase transition that changes a resume row's visible status must call `refreshResumes()` — UPLOADED, REVIEWING, DONE all qualify, not just DONE.
- **Pre-draft orphan architecture:** orphans are detected via `roles=[]` AND `session_anchor=null`. `useResumeMachine` routes them to UPLOADED phase on load. Dashboard shows them with the tertiary-color `UPLOADED` badge. Stats fold them into "any non-finalized resume" count.

Test count: 135 → 137 passing.

---

## April 17, 2026 | Honesty Stack | Tasks 1–6

**Status:** ✅ Complete — full honesty stack live, verified against real veteran resume.

Over a single day, built three layers of LLM output validation that raise the product's trust bar from "tests pass" to "resume is materially honest and identity-preserving." The motivating question: _how do we validate that the LLM's translation is both optimally written for recruiters and honestly grounded in what the veteran actually did?_

### Tasks 1–3 — Initial Honesty Stack

| Task | Status | Scope                                                                                                                                                                                                                                                                              |
| ---- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | ✅     | Grounding-first `_SYSTEM_PROMPT` with explicit non-invention and non-inflation rules. +5 tests (137 → 142).                                                                                                                                                                        |
| 2    | ✅     | `translate_app/grounding.py` — pure-Python regex validator for metric fabrication and scope-inflation verbs. `flag_translation()` wired into `ResumeDraftView` AND `ResumeChatView` responses as `bullet_flags`. `DATA_CONTRACT.md` updated both endpoints. +10 tests (142 → 152). |
| 3    | ✅     | Frontend flag-gated UX — ⚠ badge on collapsed flagged bullets, "Grounding Check" panel in expanded editor, "I verified this" checkbox. Confirm Final disabled until all flagged bullets verified.                                                                                  |

### Tasks 4–6 — Tuning Against Real Resume

Smoke test with Brandon Livrago's Army PSYOP resume + Unstructured JD revealed issues the tests couldn't catch; each was addressed with a targeted follow-up task.

| Task | Finding                                                                                                                                                                                                                                                                                                                                                                                                                                         | Fix                                                                                                                                                                                                                                                                                                                                                                                                         |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4    | Layer 1 over-correction — Claude was dropping _source-side_ metrics along with invented ones. `$110M+ in 401(k) assets` became `401(k) assets`. UX was also too heavy — requiring per-bullet confirm when most bullets had zero flags.                                                                                                                                                                                                          | Rewrote `_SYSTEM_PROMPT` with SOURCE PRESERVATION RULES (preserve source facts, never add new ones). Shifted UX from per-bullet confirm to flag-gated: unflagged bullets trusted by default; only flagged bullets need verification. +1 test (152 → 153).                                                                                                                                                   |
| 5    | Summary field was invoking invented aggregate — `"$1.2M+ in program budgets"` computed by summing real source numbers. Validator scope was bullets only; summary had no guardrails.                                                                                                                                                                                                                                                             | Added rule forbidding aggregates, new `flag_summary()` helper, wired `summary_flags` into Draft and Chat responses, extended frontend verification counter to treat summary as one more eligible flagged item. +5 tests (153 → 159).                                                                                                                                                                        |
| 6    | Claude was over-translating identity-carrying specifics — "Ukraine" → "international," "PSYOP teams" → "cross-functional teams," "red-team" → "technical support," "ION" platform name stripped, section grouping lost, summary flattened into generic PM boilerplate. For a tool serving veterans, this is product failure: ATS systems match on exact keywords (USSOCOM, PSYOP, Ukraine) and recruiters pattern-match on distinctive signals. | Added three new prompt rules: **PRESERVE ALL PROPER NOUNS VERBATIM** (rule 3), **preserve employer/command context** by prefixing parent org into each role's `org` field (rule 5), **jargon-vs-identity distinction** — translate BLUF/S-4/MOS codes but NOT PSYOP/Ukraine/red-team (rule 6), **summary fidelity** (rule 7) — preserve multi-domain signals, no generic boilerplate. +4 tests (159 → 163). |

### Final Smoke Test (Brandon Livrago resume + Unstructured JD)

All 20+ checklist items passed after Task 6:

- ✅ Every source dollar amount preserved ($110M+, $200M+, $410M, $275K+, $240K+, $950K+, $25K, 12+, 100+)
- ✅ Every proper noun preserved verbatim (Ukraine, PSYOP ×8, red-team, ION, Tier 1 SOF, UK/Canada, Moldovan NCO Academy, State Dept.'s 7th Floor, Fort Bragg, Tbilisi, Chisinau)
- ✅ Parent org prefix applied to all three Army deployment roles (`US Army Special Operations, PSYOP — ...`)
- ✅ Flynn Financial and digital marketing roles correctly _not_ prefixed with military context
- ✅ Summary preserves multi-domain signal (operations + institutional finance + digital-marketing strategy)
- ✅ Summary mentions TS/SCI, PSYOP/Special Operations
- ✅ Zero invented aggregate metrics in summary
- ✅ `bullet_flags: []` and `summary_flags: []` on a fully grounded draft (validator correctly has nothing to catch)

### Honesty Stack Architecture

```
Layer 1 — Prompt
    _SYSTEM_PROMPT (services.py) — 8 rules covering:
    • Source fact preservation (numbers, proper nouns, scope words)
    • Non-invention (no fabricated metrics, no aggregates)
    • Non-inflation (scope/seniority match input)
    • Role preservation (title, org, dates, parent command)
    • Jargon-vs-identity boundary (translate BLUF, not PSYOP)
    • Summary fidelity (multi-domain signal preserved)

Layer 2 — Validator
    translate_app/grounding.py
    • flag_bullet()    — regex scan of one bullet vs source text
    • flag_translation() — all bullets in all roles
    • flag_summary()   — reuses flag_bullet on summary field
    Wired into ResumeDraftView + ResumeChatView
    API keys: bullet_flags, summary_flags

Layer 3 — UX
    frontend/src/components/DraftPane/BulletEditor.jsx
    frontend/src/components/DraftPane/FinalizingEditor.jsx
    • ⚠ badge on collapsed flagged bullets (text-amber-400)
    • Grounding Check panel in expanded editor
    • "I verified this" checkbox only on flagged items
    • Summary gets parallel treatment when summary_flags non-empty
    • verifiedFlags Set tracks resolutions
    • Confirm Final disabled until allFlagsResolved
    • Progress: "N of M flagged items verified" OR "✓ All claims passed grounding checks"
```

### Post-Launch Backlog (noted but not blocking)

- **Qualitative-aggregate refinement** — prompt tweak to catch claims like "multi-million dollar programs" that cross unrelated role types
- **LLM-as-judge semantic fidelity pass** — catches scope inflation beyond regex (deferred from Task 2)
- **Extend validator to scan `civilian_title`** — lower fabrication risk but same-cost protection

---

Project log maintained: github.com/cjoewono/ranktorole
Last updated: April 17, 2026 — Honesty stack complete, 163 tests passing

---

## April 17, 2026 | Session 13 | Career Recon Enrichment

**Duration:** Afternoon session | **Status:** ✅ Complete

### What Was Built

Added personalized career intelligence to the Career Recon page via Claude Haiku 4.5.
When a veteran clicks a career card, the frontend fires two parallel requests:
O*NET career detail (existing) + Haiku enrichment (new). Both are resolved via
`Promise.allSettled`, so Haiku failure gracefully degrades to O*NET-only view.

### Architecture

**Backend — `onet_app/recon_enrich_service.py`**

- Shared Anthropic client from `translate_app.services._get_client()`
- Profile-aware cache key: `recon_enrich:{code}:{sha256(branch|mos|sector|skills)[:16]}`
- Incr-first ceiling check prevents TOCTOU over-count across gunicorn workers
- `strip_tags` on all LLM string outputs (stored-XSS defense)
- `CareerEnrichment` Pydantic schema with `max_length` constraints

**Five cost controls (defense in depth):**

1. Auth + profile gate
2. Per-user tiered throttle (15/day free, 25/day pro)
3. DB-backed result cache (7-day TTL)
4. 15s hard API timeout
5. Global 500/day ceiling

**Frontend — `CareerRecon.jsx`**

- `latestClickRef` ref prevents mismatched detail+enrichment on rapid card clicks
- Enrichment panel: match score badge, personalized description, transferable skills,
  skill gaps, education recommendation
- Nullish-coalesce on all enrichment fields guards against partial LLM responses

### Deliberate Exclusions

- **No resume bullets** — LLM-fabricated XYZ metrics on Recon is a liability.
  Veterans draft bullets with their real numbers in the resume builder.
- **No grounding.py changes** — Enrichment has no source-of-truth to ground against.
- **No bullet_flags/summary_flags** — Not applicable to Recon flow.

### Test Coverage

- 7 endpoint tests: auth, profile gate, invalid code, O\*NET 404, Haiku failure (503), happy path, unauthenticated
- 3 cost-control tests: cache hit skips LLM, profile change invalidates cache, global ceiling blocks call
- Final: 163 → 173 passing

### Cost Model

| Tier           | Max/day   | Max cost/day |
| -------------- | --------- | ------------ |
| Free           | 15 calls  | $0.04        |
| Pro            | 25 calls  | $0.065       |
| Global ceiling | 500 calls | $1.30        |

Expected monthly spend at 100 pro users / 10 sessions: ~$3/month (60-75% cache hit rate).

---

### Follow-up: MOS Title Resolver Arc (April 17–20)

Smoke testing after initial Session 13 merge surfaced a trust-critical
hallucination: Haiku described a Navy 1110 (Surface Warfare Officer) as
"Administrative Yeoman." Three coordinated fixes over one session closed the
gap across 5 of 6 service branches.

| Task | Finding                                                                                                                                                                                                        | Fix                                                                                                                                                                                                                                                                                                             |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Haiku given raw MOS codes fabricated titles — training data has weak coverage of military codes and no self-awareness to admit uncertainty.                                                                    | Added `_resolve_mos_title()` that hits O\*NET `/veterans/military/` for authoritative title. 30-day cache per `(branch, mos)` key. Prompt rewritten to use resolved title verbatim, with explicit "do not invent" fallback when miss. +3 tests (173 → 176).                                                     |
| 2    | Diagnostic revealed O\*NET has zero coverage of Navy officer designators (1110, 1120, 1310, etc.) — not indexed by code or by title search. All other branches' officers resolve fine (Army 17A, Marine 0302). | Added `NAVY_OFFICER_DESIGNATORS` dict — ~30 codes covering URL, RL, Staff Corps, LDO, CWO communities. Resolver checks local dict before O\*NET fallback. +2 tests (176 → 178).                                                                                                                                 |
| 3    | Follow-up diagnostic surfaced two more gaps: AF/USSF officer AFSCs (11F, 14N) only indexed at full-specialty level (11F1B, 14N1M), and Coast Guard had zero O\*NET coverage entirely.                          | Added prefix-match to resolver: when exact match fails for AF/USSF, accept first entry whose code starts with user's input, and strip sub-specialty from title ("Fighter Pilot, A-10" → "Fighter Pilot") to avoid misrepresenting aircraft. Added `COAST_GUARD_RATINGS` dict (~21 codes). +5 tests (178 → 183). |

### Coverage Matrix (Post-Arc)

| Branch       | Enlisted              | Officer     | Source                                            |
| ------------ | --------------------- | ----------- | ------------------------------------------------- |
| Army         | ✅                    | ✅          | O\*NET exact match                                |
| Navy         | ✅ (2-letter ratings) | ✅          | O\*NET (enlisted) + local dict (officers)         |
| Air Force    | ✅                    | ✅          | O\*NET exact (enlisted) + prefix match (officers) |
| Marine Corps | ✅                    | ✅          | O\*NET exact match                                |
| Coast Guard  | ✅                    | ⏳ deferred | Local dict (enlisted only)                        |
| Space Force  | ✅                    | ✅          | O\*NET prefix match (shared with AF)              |

Known gaps carried to post-launch backlog:

- Coast Guard officer designators (smaller user population, idiosyncratic system)
- Navy rating with pay grade suffix (IT2 doesn't resolve; IT does)
- Qualitative aggregate refinement in resume translator (unrelated)

### Key Learnings

- **Real-data smoke testing catches what tests don't.** The 176 passing tests
  validated code paths but couldn't surface the hallucination — only a real
  Navy officer profile + real career click did. Mocked tests never reached the
  prompt-content level. This is the same lesson from the honesty stack
  sessions: veterans using real profiles expose failures synthetic data misses.
- **Haiku confidently invents when lacking ground truth.** The "do not invent"
  prompt rule alone would not have been sufficient — Haiku doesn't have
  accurate self-awareness of its own knowledge gaps for niche domains like
  military codes. The structural fix (ground truth injection) is what works.
- **O\*NET coverage is uneven across branches and enlisted/officer lines.**
  Navy officers missing entirely, AF officer codes indexed at wrong
  granularity, CG missing wholesale. Building a product on O\*NET requires
  mapping these gaps and filling them with local data.
- **Split the fix into sequenced commits.** Three commits (resolver + Navy dict
  - AF/CG) is more reviewable and revertable than one sprawling commit.
    Standard hygiene but especially valuable when the scope kept growing during
    the session.

---

## April 20, 2026 | Session 14 | Redis Cache Backend

**Status:** ✅ Complete — Redis infrastructure swap, zero test regressions, all smoke tests passed

### Changes Shipped (Two Commits)

**Commit 1 — `feat(infra): provision Redis container`**

- `docker-compose.yml` — `redis:7-alpine` service with healthcheck, RDB persistence (`save 3600 1 300 100 60 10000`), 256mb LRU cap, `redis_data` named volume. `backend.depends_on` waits for Redis healthy.
- `docker-compose.override.yml` — Redis port 6379 exposed to host for dev `redis-cli` debugging.
- `backend/requirements.txt` — `django-redis==5.4.0`.

**Commit 2 — `feat(cache): activate Redis backend`**

- `backend/config/settings.py` — `CACHES` swapped to `django_redis.cache.RedisCache` gated on `REDIS_URL`. LocMemCache fallback when env unset (CI, local-without-docker). `IGNORE_EXCEPTIONS=False`, `KEY_PREFIX='rtr'`.
- `backend/conftest.py` — `force_local_memory_cache` autouse fixture keeps test suite Redis-free.
- `backend/config/urls.py` — `/health/` now probes cache backend via set/get round-trip.
- `.env.example` — documented `REDIS_URL`.

### Architectural Wins

1. **Atomic global daily ceiling counter.** `_check_and_increment_global_ceiling()` was using `cache.incr()` with a `get-then-set` fallback under `DatabaseCache` — a TOCTOU race across gunicorn workers that could under-count rejections. Redis `INCR` is atomic. Verified live: `rtr:1:recon_enrich_global:2026-04-20` key landed during Checkpoint 2.
2. **Throttle latency reduction.** Per-request throttle lookups drop from ~2-5ms (DB query) to ~0.2ms (Redis hit).
3. **Foundation for Session 15.** Response caching for O\*NET proxy + resume list endpoint.

### Dev Workflow Impact

`docker compose up -d` now starts Redis alongside db + backend. No code changes in cache consumers — `django.core.cache` API is backend-agnostic, so all existing cache touchpoints in `onet_app/views.py`, `translate_app/throttles.py` work unchanged.

### Verification

- BASELINE tests: 183
- FINAL tests: 183 — zero regressions
- `/health/` returns 200 with both DB and cache green
- 6 live keys in Redis after smoke test traffic
- Confirmed key shapes: `rtr:1:throttle_user_<scope>_<tier>_<uuid>`, `rtr:1:recon_enrich:<onet_code>:<sha256>`, `rtr:1:recon_enrich_global:<date>`
- Recon enrichment payload TTL verified at ~604800s (7 days)
- Fail-loud behavior confirmed: Redis stop → 503, start → 200
- RDB persistence confirmed: DBSIZE survives `docker compose restart redis`

### Lessons Learned

**`docker compose restart` does NOT re-read env_file.** During Checkpoint 2 verification, `/health/` reported `cache: true` but Redis was empty. Root cause: `REDIS_URL` was added to `.env` but the running backend container's environment was frozen from its original creation — `docker compose restart backend` bounced the process inside the same container without re-reading `.env`. Fix: `docker compose up -d --force-recreate backend`. Pattern documented in CLAUDE.md.

## April 20, 2026 | Session 15 | Redis-Enabled Optimizations

**Status:** ✅ Complete — cache-aside pattern shipped for O\*NET proxy + resume list. 183 → 198 tests, zero regressions.

### Changes Shipped (One Commit)

**`feat(cache): cache-aside for O*NET proxy + resume list`** (`518b378`)

Two new utility modules (cache key builders + TTL constants):

- `backend/onet_app/cache_utils.py` — `search_cache_key`, `military_search_cache_key`, `career_detail_cache_key`, `ONET_RESPONSE_CACHE_TTL = 6 hours`
- `backend/translate_app/cache_utils.py` — `resume_list_cache_key`, `invalidate_resume_list_cache`, `RESUME_LIST_CACHE_TTL = 1 hour`

O\*NET response caching (`backend/onet_app/views.py`):

- `OnetSearchView` — caches `(occupations, skills)` payload by keyword
- `OnetMilitarySearchView` — caches `(military_matches, careers)` by `(keyword, branch)`
- `OnetCareerDetailView` — caches normalized career payload by O\*NET-SOC code
- Empty/error responses NOT cached (no poisoning)

Resume list caching with explicit invalidation (`backend/translate_app/views.py`):

- `ResumeListView.get` — cache-aside read
- Invalidation hooks added to all six write paths:
  - `ResumeUploadView.post` (create)
  - `ResumeDetailView.delete` (delete)
  - `ResumeDraftView.post` (save)
  - `ResumeChatView.post` (save)
  - `ResumeFinalizeView.patch` (save)
  - `ResumeReopenView.patch` (save)

New test files (15 tests):

- `backend/onet_app/tests_cache.py` (8) — cache hits, miss-on-different-keys, no-cache-on-empty, no-cache-on-404
- `backend/translate_app/tests_cache.py` (7) — cache hits, user isolation, write-path invalidation, post-invalidation freshness

### Architectural Wins

1. **O\*NET upstream call reduction.** Career detail endpoint previously made 5 upstream API calls per request (overview + skills + knowledge + technology + outlook). Now: 5 calls on cache miss, 0 on hit. Search endpoint: up to 4 upstream calls reduced to 0 on hit. With a 6-hour TTL and typical browse patterns, ~95% of upstream calls eliminated.
2. **Resume list latency drop.** Dashboard load no longer queries Postgres for the resume list on every navigation. Cache-aside with explicit invalidation guarantees no stale data — every write path drops the cached entry, next read repopulates from DB.
3. **Cache-aside pattern with proper invalidation discipline.** Six invalidation hooks across all write paths. Per-user isolation verified by test (`test_user_a_write_does_not_invalidate_user_b_cache`). 1-hour TTL serves as safety net only, not the primary freshness mechanism.

### Verification

- BASELINE tests: 183
- FINAL tests: 198 (+15) — zero existing test regressions
- 1 resume_list key live in Redis
- 6 O\*NET cache keys live in Redis
- Browser smoke test: dashboard reload visibly snappier; new resume upload appears immediately on next dashboard load (proves invalidation); duplicate Recon career click is instant (proves cache hit)

### Known Tradeoff (Post-Launch Hardening Candidate)

With `IGNORE_EXCEPTIONS=False` (set in Session 14 to prevent silent throttle bypass) and cache invalidation now in normal write paths, a Redis outage will surface as 500 errors on resume create/save/delete operations. The healthcheck catches Redis outages immediately, but during the outage window users cannot upload or modify resumes.

Two future-Cal options:

1. Wrap each `invalidate_resume_list_cache()` call in `try/except` so write paths degrade gracefully (cache may serve stale until TTL expires, but writes succeed).
2. Switch to `IGNORE_EXCEPTIONS=True` and add view-level throttle bypass detection.

Option 1 is the simpler fix and preserves throttle integrity. Deferred to Session 16 or later.

---

## April 20, 2026 (evening) | Throttle rebalance for launch

**Status:** ✅ Shipped.

Pro-tier draft cap was 5/day — too tight for realistic burst-day usage
(3-5 applications in a day) and for own-testing. Rebalanced to launch
values based on per-draft cost (~$0.057 Sonnet 4) and realistic usage
patterns.

New pro caps: user_upload 20/day, user_draft 15/day, user_chat 75/day,
user_finalize 20/day. Free tier unchanged. Global 500/day ceiling
unchanged — caps absolute worst-case spend at ~$30/day regardless of
per-user values.

Free→pro conversion driver (1/day free draft cap) is deliberately
preserved at 1/day. The conversion ask is "unlock unlimited tailoring
for real job search" — not "unlock a bigger free tier."

Settings change only. No test changes needed. 210 tests still passing.

---

---

## April 20, 2026 (evening) | 429 daily-limit UX

**Status:** ✅ Shipped.

Closed the known pre-launch backlog item: pro-tier 429 responses now
carry a structured `DAILY_LIMIT_REACHED` code and `retry_after_seconds`,
matching the existing pattern for free-tier 403 `TAILOR_LIMIT_REACHED`.

Frontend changes:

- UpgradeModal gained a `variant` prop. "upgrade" (default) keeps the
  existing Stripe checkout CTA for free-tier quota. "wait" renders a
  dismiss-only modal for pro-tier daily caps with a human-readable
  reset time ("Resets in 12 hours").
- useResumeMachine routes 429 DAILY_LIMIT_REACHED from draft and chat
  endpoints into the "wait" modal. Phase reset is built into
  DAILY_LIMIT_HIT: DRAFTING resets to UPLOADED; REVIEWING/FINALIZING
  stays put.
- apiFetch generic fallback: any 429 without a specific code is
  surfaced as "You've hit a daily limit. Try again later." instead of
  DRF's default "Expected available in 75635 seconds."
- Daily-limit modal rendered at ResumeBuilder level (not per-component)
  so it appears on top of both split and upload views.

Backend changes:

- Custom DRF exception handler (`tiered_throttle_exception_handler`)
  in `translate_app/throttles.py`, wired globally via
  `REST_FRAMEWORK['EXCEPTION_HANDLER']`.
- Only intercepts `Throttled` exceptions; all other errors use DRF's
  default handler.

Scope: draft + chat routed to modal. Upload, finalize, ONET, Recon
covered by apiFetch generic fallback. Login/register/anon throttles
(anti-enumeration) unchanged — they are not user-tier daily caps.

Test count: 210 → 212 (+2 tests for throttle response shape).

---

## April 20, 2026 (evening) | Tailoring v2.1: mid-sentence noun mirroring

**Status:** ✅ Shipped.

Two smoke tests of v2 (defense JD and non-defense JD) showed v2
tailors verbs reliably but consistently misses distinctive noun
phrases in the JD. Both runs also showed zero flags and full
identity preservation — the honesty guarantee is intact, but the
tailoring floor on non-defense JDs has noun-phrase-shaped holes.

v2.1 extensions:

1. R3(a) and R3(b) now explicitly call for noun-phrase mirroring,
   not just verb swaps. R3(a) instructs Claude to sweep the JD for
   distinctive nouns and named responsibilities ('stakeholder
   navigation', 'team orchestration', 'budget tracking', etc.) and
   mirror them into bullets where the veteran's actual activity
   supports each phrase.

2. R3(c) expanded from "do not fabricate skills/tools" to also cover
   "do not imply unearned responsibility". Budget management ≠ P&L
   management. The rule now names P&L as the canonical example of a
   JD phrase that implies authority the veteran doesn't hold, even
   when the activity is adjacent.

3. Example 4 added to DEMONSTRATED TRANSFORMATIONS: a worked example
   using the veteran's $950K+ COR work, showing both (a) how to
   mirror 'multi-stakeholder program delivery' from the JD and (b)
   how to explicitly NOT mirror 'P&L management'. The 'What stayed
   limited' commentary teaches the guardrail by demonstration, not
   just by rule.

Grounding validator unchanged — noun-phrase reframing does not
introduce fabricated numerics or scope-inflation verbs. The
implied-responsibility guardrail is prompt-level for now; Option A
(unearned-claim validator, next task) is where this line gets
enforced deterministically.

Test count: 212 → 216 (+4 tests covering R3 extension, Example 4
presence, and P&L guardrail enforcement).

---

## April 20, 2026 (late evening) | Tailoring v2.2: HARD LIMITS block

**Status:** ✅ Shipped.

v2.1 shipped earlier today with R3 extended for noun-phrase mirroring
and R3(c) expanded to cover unearned-responsibility claims (P&L as the
canonical example). Smoke test against Aquent Engagement Manager JD +
Brandon PSYOP resume showed:

Positive: noun mirroring worked — "stakeholder navigation" and "team
orchestration" correctly pulled into bullets where activity supported
them.

Regression: the P&L guardrail failed. Role 2 bullet 1 output "Managed
P&L for two $240K+ program contracts as COR" — a false responsibility
claim (COR ≠ P&L authority). Executive summary fabricated a "$1.4M+
program portfolio" by summing separate source numbers (rule P2
violation that wasn't caught). ATS FIT ASSESSMENT self-certified "P&L
management" as a Strong match, upstream of the bullet.

Diagnosis: the guardrail was a carve-out clause inside R3(c) while
R3(a) was a strong positive directive to mirror JD nouns. Under
pressure, the positive directive dominated and the exception clause
eroded. Architectural, not a language problem.

Structural fix (v2.2): promoted guardrails OUT of R3 into a new named
block "HARD LIMITS" sitting alongside PRESERVATION RULES and REWRITE
RULES. Four hard limits, each enumerating specific forbidden phrases
rather than describing patterns:

- H1: P&L-adjacent phrases forbidden unless source explicitly
  establishes profit-and-loss authority. COR and budget management
  explicitly carved out as NOT establishing P&L authority.
- H2: aggregate totals across source numbers forbidden (concretizes
  the P2 rule that was abstract).
- H3: credentials/clearances/certifications absent from source cannot
  be added to output.
- H4: ATS FIT ASSESSMENT Strong matches must be grounded in source —
  closes the Stage 1 self-certification path.

R3(c) slimmed back to skill/tool fabrication only, with a pointer to
HARD LIMITS for the rest. Example 4 commentary updated to name H1 as
the enforcing rule.

HARD LIMITS placed BEFORE PRESERVATION RULES and REWRITE RULES in
prompt order. This changes the authority gradient: Claude reads hard
limits first, then positive rules. Positive rules cannot pressure
Claude past the hard limits because the hard limits are structurally
primary, not an exception clause.

Test count: 216 → 223 (+7 tests covering HARD LIMITS block, each rule
H1-H4, Example 4 commentary update, R3(c) simplification).

Option A (grounding.py unearned-claim validator) remains the next
task — it adds Layer 2 deterministic catches for P&L-class phrases
and aggregate totals as a defense-in-depth layer behind this prompt
fix.

---

## April 20, 2026 (late evening) | Option A: grounding.py unearned-claim validator

**Status:** ✅ Shipped.

Two consecutive prompt iterations (v2.1, v2.2) could not reliably
enforce the P&L-class claim prohibition under JD-anchoring pressure.
The Aquent JD names 'P&L' as a specific priority; noun-mirroring
pressure pulled Claude to match the phrase despite the HARD LIMITS H1
block sitting structurally primary.

Correct response: accept that prompt-layer enforcement of this claim
class is unreliable, and move enforcement to Layer 2 (validator) where
it is deterministic. This is the honesty stack working as designed —
Layer 1 sets the goal, Layer 2 catches what Layer 1 cannot, Layer 3
puts the user in the loop via flag-gated verify UX.

Extended `grounding.py` with `flag_unearned_claims(text, source_text)`
covering four categories:

1. P&L-class phrases (always flagged). Flag message explains the
   COR / budget-management carve-out so the user can verify or reject.
2. Skill/tool claims (flagged when in output but not source). AI/ML,
   cloud, named languages, SaaS, project management platforms.
3. Credentials (flagged when in output but not source). TS/SCI, PMP,
   Series 7, AWS Certified, etc. Flag message emphasizes
   verification harm to the veteran.
4. Dollar-amount aggregates (flagged when output dollar amount is not
   verbatim-present in source). Deterministic backstop for H2.

Wired into existing `flag_bullet`; `flag_summary` picks it up
transitively. No API shape change — new flag strings flow through
existing `bullet_flags` and `summary_flags` response fields. Zero
frontend changes.

Test count: 223 → 241 (+18 tests across all four categories plus
integration with flag_bullet and edge cases).

Known scope: this is launch-ready, not exhaustive. Semantic stretches
that don't match the blocklists (e.g., 'technical advisory' when
source said 'red-team') remain uncaught by code. Option D (user
responsibility banner) closes that gap by acknowledging the user owns
the final product.

---

## April 21, 2026 (early morning) | Bugfix: CHAT_UPDATED reducer dropped flags

**Status:** ✅ Shipped.

During Option A smoke testing, observed the draft-path
(`handleGenerateDraft` → `DRAFT_RECEIVED`) correctly propagates
`bullet_flags` / `summary_flags` from backend response into state.
The chat-path (`handleChatSend` → `CHAT_UPDATED`) did not — the
dispatcher sent the flags in the action payload but the reducer
ignored them. Flags from the initial draft persisted stale through
any chat refinement turn.

Fix: 2-line addition to `CHAT_UPDATED` using the `??` pattern already
established in `AI_SUGGESTIONS_RECEIVED`. Flags now flow through
every chat turn correctly.

No tests changed — frontend still has no test framework. Verified
via manual smoke test. Backend test count unchanged at 241.

---

## April 21, 2026 (early morning) | Option D: user responsibility banner

**Status:** ✅ Shipped. Commit `4772608`.

Closes the honesty stack loop. Layers 1–3 (prompt guardrails, deterministic
validator, flag-gated verify checkboxes) catch fabricated metrics, scope
inflation, unearned credentials, and P&L-class claims. Semantic stretches
that don't match blocklists (e.g., 'technical advisory' when source said
'red-team') remain uncaught by code. The banner makes explicit that the
user owns the final resume.

Single JSX block in `FinalizingEditor.jsx` between the "Edit & Finalize"
h2 and the Mission Headline input. Non-dismissable. Uses existing design
tokens — amber FINAL REVIEW label mirrors the summary Grounding Check
pattern. No state, no props, no callbacks.

Test count unchanged at 241 (no backend touched, frontend has no test
framework). Frontend build clean.

## April 21, 2026 (early morning) | is_finalized contract resolved

**Status:** ✅ Resolved. Docs-only.

DATA_CONTRACT.md said `POST /chat/` returns 409 when `is_finalized=True`.
Code returned 200. Active test asserted 200. Three things disagreed.

Decision (Cal): chat stays open after finalize so users can continue
refining via chat. Code already matches this behavior. DATA_CONTRACT.md
updated in four locations to reflect the actual contract: chat endpoint
error responses (409 removed), chat behavior section (note added that
chat remains available post-finalize), finalize endpoint behavior (note
added that subsequent finalize calls overwrite previous final state),
data storage section (`is_finalized` description clarified — boolean
marker, does not lock chat).

No code changes. No test changes. Test count unchanged at 241.

---

## April 22, 2026 | is_finalized gate removed from ResumeChatView

**Status:** ✅ Code now matches the chat-stays-open decision.

Prior state: ResumeChatView.post returned 409 when is_finalized=True.
Test asserted 409. DATA_CONTRACT had internal contradictions.
The April 21 decision in PROJECTLOG ("chat stays open after finalize")
was documented but the code change was never made.

This commit:

- Removed the 5-line 409 gate from ResumeChatView.post
- Rewrote test_finalized_resume_chat_returns_409 as
  test_finalized_resume_chat_remains_available, asserting 200
- Updated DATA_CONTRACT.md line ~562 (is_finalized storage
  description) to reflect chat-stays-open
- Resolved TASKS.md entries for the is_finalized gate work

Test count unchanged at 234 (test rewritten in place, not added
or removed).

Project log maintained: github.com/cjoewono/ranktorole
Last updated: April 22, 2026 — is_finalized chat-stays-open shipped, 234 tests passing
