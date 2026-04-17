# TASKS.md

## Status Key

- [ ] Not started
- [~] In progress
- [x] Done
- [!] Blocked

---

## Completed — Phases 1–3 (Sessions 01–02)

### Infrastructure

- [x] Initialize Django project + app structure
- [x] Initialize React + Vite + Tailwind
- [x] Write `docker-compose.yml` (frontend, backend, db, nginx)
- [x] Write Nginx config
- [x] Configure `.env` and `.env.example`
- [x] Verify full stack boots via `docker compose up --build`

### Authentication

- [x] Install and configure `djangorestframework-simplejwt`
- [x] Build `/api/v1/auth/register/` endpoint
- [x] Build `/api/v1/auth/login/` endpoint (returns access + refresh tokens)
- [x] Build `/api/v1/auth/refresh/` endpoint
- [x] Build `/api/v1/auth/logout/` endpoint
- [x] Apply JWT middleware to all non-auth endpoints
- [x] Build frontend login/register forms
- [x] Hybrid JWT: access token in memory, refresh token in httpOnly cookie
- [x] Protect all frontend routes (redirect to login if no token)
- [x] Install `social-auth-app-django`
- [x] Configure Google OAuth credentials in `.env`
- [x] Build `/api/v1/auth/google/` endpoint
- [x] Frontend Google login button

### Database Models

- [x] User model (UUID PK, extend AbstractUser)
- [x] Resume model (UUID PK, user FK, military_text, job_description, session_anchor, approved_bullets, rejected_bullets, output JSON, created_at)
- [x] Contact model (UUID PK, user FK, name, email, company, role, notes)
- [x] Run and verify migrations

### Translation Service (original single-shot — superseded by Phase 4)

- [x] Create `translate_app` Django app
- [x] Write `context.py` — DecisionsLog, RollingChatWindow
- [x] Write `compress_session_anchor()` and `build_messages()` in `services.py`
- [x] Build `MilitaryTranslation` Pydantic schema
- [x] Build `POST /api/v1/translations/` view
- [x] Write pytest tests for `context.py` and `services.py`

### Frontend (original)

- [x] Build layout + navigation (React Router DOM)
- [x] Build TranslateForm component
- [x] Build ResumeOutput component
- [x] Build resume history page (list saved resumes)
- [x] Lazy load components
- [x] Connect all forms to backend API via relative paths

### Contacts CRUD

- [x] Build `contact_app` views (list, create, update, delete)
- [x] Connect frontend Contacts page to API

---

## Completed — Phase 4: PDF Flow + Intelligent Refinement (Sessions 04–05)

### Step 0 — Code Review & Smoke Test

- [x] `docker compose up --build` — verify all 4 services start clean
- [x] Run pytest — verify all tests pass
- [x] Verify GET `/api/v1/resumes/` returns 200
- [x] Verify GET `/api/v1/contacts/` returns 200
- [x] Code review: `translate_app/services.py`, `context.py`, `views.py`
- [x] Code review: `user_app/views.py` (JWT hybrid pattern)
- [x] Code review: frontend `AuthContext.jsx` + `client.js`
- [x] Fix all issues found before starting Step 1

### Step 1 — Migration & Dependencies

- [x] Add `is_finalized = BooleanField(default=False)` to Resume model
- [x] Run `makemigrations` + `migrate`
- [x] Add `pymupdf==1.24.11` to `requirements.txt`
- [x] Rebuild Docker image

### Step 2 — PDF Upload Endpoint

- [x] Build `POST /api/v1/resumes/upload/` view (multipart/form-data, MIME + magic-bytes + size validation, PyMuPDF extraction)
- [x] Register URL in `resume_urls.py`
- [x] Update `ResumeSerializer` to handle partial state (blank fields)

### Step 3 — Draft Endpoint

- [x] Expand `MilitaryTranslation` Pydantic schema with `clarifying_question` and `assistant_reply`
- [x] Update system prompt to instruct Claude to generate 1 targeted clarifying question
- [x] Build `POST /api/v1/resumes/{id}/draft/` view
- [x] Register URL in `resume_urls.py`
- [x] Tests added (TestResumeDraftView)

### Step 4 — Chat Endpoint

- [x] Build `POST /api/v1/resumes/{id}/chat/` view (DB-backed chat history)
- [x] Register URL in `resume_urls.py`
- [x] Handle 409 if `is_finalized=True`
- [x] Write pytest tests for chat endpoint

### Step 5 — Finalize Endpoint

- [x] Build `PATCH /api/v1/resumes/{id}/finalize/` view
- [x] Register URL in `resume_urls.py`
- [x] Write pytest tests for finalize endpoint

### Step 6 — Frontend: Split-Pane Builder

- [x] PDF dropzone (PDF only, upload before draft)
- [x] Frontend state machine: IDLE → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE
- [x] Split-pane layout (draft left, chat right)
- [x] Left pane: read-only cards in REVIEWING; editable in FINALIZING
- [x] Right pane: chat messages (clarifying_question as initial assistant message)
- [x] "Generate Draft" button → `POST /{id}/draft/`
- [x] Chat input → `POST /{id}/chat/`
- [x] "Approve & Finalize" button → FINALIZING state
- [x] "Confirm Final" button → `PATCH /{id}/finalize/`
- [x] `api/resumes.js` with all endpoint functions
- [x] Dashboard shows `is_finalized` badge
- [x] Export PDF (jsPDF) from DONE phase
- [x] Redline diff vs `ai_initial_draft` in FINALIZING

### Step 7 — End-to-End Smoke Test

- [x] Upload PDF
- [x] Paste real job description
- [x] Verify draft + clarifying question returned
- [x] Answer question in chat, verify draft updates
- [x] Inline-edit a bullet
- [x] Finalize and verify `is_finalized=True` on dashboard

---

## Completed — Session 06 (April 10)

### API Layer Refactor (Frontend)

- [x] Add `APIError` class + `handleResponse` helper to `client.js`
- [x] Refactor `apiFetch` to return parsed data, throw `APIError`
- [x] Eliminate manual error handling from `resumes.js`, `auth.js`, `contacts.js`, `translations.js`
- [x] Extract `exportPDF` to `frontend/src/utils/pdfExport.js`

### Backend Service Layer

- [x] Add `ChatResult` dataclass to `services.py`
- [x] Migrate chat history management into `call_claude_chat`
- [x] Update `ResumeChatView` to consume `ChatResult`
- [x] Update 4 `TestResumeChatView` tests to mock `ChatResult` return type
- [x] 77/77 tests passing

---

## Completed — Session 07 (April 11)

### SPA Shell Refactor

- [x] Implement AppShell pattern (always-mounted NavBar, pages shown/hidden via CSS)
- [x] Add `ResumeContext` (`frontend/src/context/ResumeContext.jsx`)
- [x] Extract `PageHeader` shared component
- [x] Refactor Dashboard + Contacts to use `PageHeader`, remove NavBar import
- [x] Refactor `ResumeBuilder` to accept `setFullscreen` prop, handle DONE phase
- [x] Delete `ProtectedRoute.jsx` (dead code)
- [x] Add catch-all redirect to `/dashboard` for unknown paths
- [x] Verify frontend build passes, 77 backend tests pass

### Frontend Component Decomposition

- [x] Extract state machine into `frontend/src/hooks/useResumeMachine.js`
- [x] Reduce `ResumeBuilder.jsx` to JSX-only (1 hook call, no logic)
- [x] Split `DraftPane.jsx` into `DraftPane/` directory (DiffView, BulletEditor, FinalizingEditor, index)
- [x] Delete flat `DraftPane.jsx`
- [x] Verify Vite builds 441 modules with 0 import errors
- [x] 77/77 backend tests passing

---

## Completed — Session 08 (April 11)

- [x] Code review fixes — `fetchOnetSkills` crash, `ProtectedRoute` removal, profile gate in AppShell, `_build_profile_block` DRY helper, dead `call_claude` removal, Anthropic client singleton, throttles on `FinalizeView` + `OnetSearchView`, `ErrorBoundary`, legacy dead code purge (`TranslationView`, `translations.js`, `context.py`)

---

## Completed — Tiered Throttle (April 12)

- [x] `User.tier` field (free/pro) + migration 0004
- [x] `TieredThrottle` base class + 5 subclasses in `throttles.py`
- [x] `TIERED_THROTTLE_RATES` in `settings.py`
- [x] 20 throttle tests added

---

## Completed — HTTPS/SSL Deployment Prep (April 13)

- [x] `settings.py` HSTS fix + `CSRF_TRUSTED_ORIGINS`
- [x] `nginx/default.conf` SSL termination rewrite
- [x] `docker-compose.yml` port 443 + cert volumes
- [x] `.env.example` expanded with all production vars

---

## Completed — Security Hardening (April 13)

- [x] Input validation: JD 10–15k, chat 2k, finalize field limits, contact limits
- [x] `RegisterThrottle` (5/hour)
- [x] Login/register error normalization (anti-enumeration)
- [x] `strip_tags` on AI output
- [x] `get_user_resume` helper extracted
- [x] Type hints on all view methods
- [x] Docstrings on all `services.py` functions
- [x] 13 new tests (97 total)

---

## Completed — Session 10 (April 13)

### Career Recon

- [x] `OnetMilitarySearchView`: GET `/api/v1/onet/military/`
- [x] `OnetCareerDetailView`: GET `/api/v1/onet/career/{code}/`
- [x] `onet_app/tests.py`: 11 tests (108 total)
- [x] `frontend/src/api/onet.js`: `searchMilitaryCareers`, `getCareerDetail`
- [x] `frontend/src/pages/CareerRecon.jsx`: SEARCH → RESULTS → DETAIL
- [x] `/recon` route wired in `App.jsx` + `NavBar.jsx`

### O\*NET v2 API Migration

- [x] All three O\*NET proxy views migrated to `api-v2.onetcenter.org`
- [x] `X-API-Key` header auth via `ONET_API_KEY` env var
- [x] Response shape fixes (`military_match`, `what_they_do`, skills/knowledge categories, technology shape, `job_outlook`)
- [x] Test mocks updated for v2 shapes
- [x] 115/115 tests passing

---

## Completed — Billing / Stripe (April 14)

- [x] User model: `stripe_customer_id`, `subscription_status`, `resume_tailor_count`, `last_reset_date`
- [x] `SubscriptionAuditLog` model (append-only, unique `stripe_event_id`)
- [x] `billing_services.py` — Checkout, Portal, webhook verification, idempotency keys
- [x] `billing_views.py` — 4 endpoints (checkout, portal, status, webhook)
- [x] `billing_throttles.py` — `CheckoutThrottle` 5/min (anti card-testing)
- [x] `billing_urls.py` mounted at `/api/v1/billing/`
- [x] `permissions.py` — `IsProOrUnderLimit` (daily counter) + `ChatTurnLimit` (permanent per-resume counter)
- [x] `UserSerializer` exposes `subscription_status`, `resume_tailor_count`, `last_reset_date` (read-only)
- [x] Settings: `STRIPE_*` vars, `FREE_TIER_DAILY_LIMITS`, `FREE_TIER_CHAT_LIMIT`
- [x] `stripe==11.1.1` added to `requirements.txt`
- [x] Frontend: `api/billing.js`, `UpgradeModal.jsx`
- [x] Tests: `test_billing.py` — signature verification, idempotency, status→tier, checkout/portal/status flows

---

## Completed — Pre-Deployment Audit (April 15)

- [x] CVE patches: Django 4.2.16→4.2.30, simplejwt 5.3.1→5.5.1, requests 2.32.3→2.33.0, cryptography 46.0.6→46.0.7
- [x] Intentional pins documented: `social-auth-app-django 5.4.2` (Django 5.1 blocker), `anthropic 0.40.0` (SDK breaking changes)
- [x] Vite/esbuild vuln deferred (dev-only, no prod exposure)
- [x] `Resume.chat_turn_count` migration 0005 applied
- [x] All migrations in sync between `models.py` and `migrations/`
- [x] 132 backend tests passing, zero warnings
- [x] Unused imports cleaned; zero `console.log` in frontend bundle
- [x] `backend/conftest.py` verified — `autouse` MagicMock on `anthropic.Anthropic` client
- [x] Production `settings.py`: HSTS, `CSRF_TRUSTED_ORIGINS`
- [x] `nginx/default.conf`: SSL termination + HTTP → HTTPS redirect
- [x] `docker-compose.yml`: port 443 + `/etc/letsencrypt` read-only volume
- [x] `.env.example` expanded to cover every production var
- [x] Docs sync pass: `README.md` (new), `ARCHITECTURE.md`, `CLAUDE.md`, `DATA_CONTRACT.md`, `SECURITY.md`, `PROJECTLOG.md`, `TASKS.md`; `AGENTS.md` annotated historical

---

## Phase 5 — EC2 Deployment (current sprint)

### DNS + Infrastructure

- [ ] Point `cjoewono.com` and `www.cjoewono.com` A records at EC2 public IP
- [ ] Confirm EC2 security group: 80/443 open to world, 22 from admin IP only, no 8000 or 5432
- [ ] Install `docker.io`, `docker-compose-plugin`, `certbot` on EC2

### Certificates

- [ ] `sudo certbot certonly --standalone -d cjoewono.com -d www.cjoewono.com`
- [ ] Verify cert files present at `/etc/letsencrypt/live/cjoewono.com/`
- [ ] Add renewal cron: `0 */12 * * * certbot renew --quiet && docker compose exec nginx nginx -s reload`

### Application Config

- [ ] Create production `.env` on host with `DEBUG=False`, rotated `SECRET_KEY`, real DB password, production `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`
- [ ] Set `GOOGLE_OAUTH_REDIRECT_URI=https://cjoewono.com/auth/google/callback`
- [ ] Set `STRIPE_CHECKOUT_SUCCESS_URL` and `STRIPE_CHECKOUT_CANCEL_URL` to production URLs
- [ ] Google Cloud Console: add `https://cjoewono.com/auth/google/callback` as authorized redirect
- [ ] Stripe dashboard: add live webhook endpoint `https://cjoewono.com/api/v1/billing/webhook/` and copy signing secret into `.env`

### Deploy + Verify

- [ ] `docker compose up --build -d`
- [ ] `docker compose exec backend python manage.py migrate`
- [ ] Smoke test: register, login, upload PDF, generate draft, chat turn, finalize, export PDF
- [ ] Smoke test: Stripe Checkout → webhook → user flips to Pro
- [ ] Smoke test: Career Recon search and detail

---

## Blocked

None.

---

## Completed — April 16, 2026 (Sessions 11 + 12)

- [x] Chat counter serializer fix + CHAT_LIMIT_REACHED UI
- [x] Initial docker-compose.override.yml for dev bind mount
- [x] Dev bind mount — backend hot-reload on host file changes
- [x] Reopen regression fix — explicit click required
- [x] Tailor-limit UpgradeModal (free-tier 1/day quota)
- [x] Pre-draft orphan resumability — UPLOADED phase + badge
- [x] Dashboard refresh on all phase transitions (UPLOADED/REVIEWING/DONE)
- [x] Test count: 132 → 137 passing

## Completed — April 17, 2026 (Honesty Stack)

- [x] Task 1 — Grounding-first `_SYSTEM_PROMPT` (non-invention, non-inflation)
- [x] Task 2 — `translate_app/grounding.py` validator; `bullet_flags` on Draft + Chat
- [x] Task 3 — Flag-gated UX (⚠ badge, Grounding Check panel, verify checkbox, Confirm Final gating)
- [x] Task 4 — SOURCE PRESERVATION RULES rewrite; shifted from per-bullet to flag-gated UX
- [x] Task 5 — Summary honesty (`flag_summary`, `summary_flags`, summary verification in UX)
- [x] Task 6 — Identity preservation (proper nouns verbatim, employer/command context, jargon/identity boundary, summary fidelity)
- [x] Smoke-tested against real veteran resume (Brandon Livrago + Unstructured JD) — all acceptance criteria passed
- [x] Test count: 137 → 163 passing

## Completed — April 17, 2026 (Session 13 — Career Recon Enrichment)

- [x] ReconEnrichThrottle — 15/day free, 25/day pro
- [x] CareerEnrichment Pydantic schema (match_score clamped 0-100, max_length constraints)
- [x] recon_enrich_service.py — Haiku 4.5 via shared Anthropic singleton
- [x] DB-backed result cache (profile-aware SHA256 keys, 7-day TTL)
- [x] Global 500/day ceiling with incr-first atomic pattern
- [x] 15s hard timeout on Haiku API call
- [x] _normalize_career_data() helper extracted and shared
- [x] ReconEnrichView: POST /api/v1/onet/enrich/
- [x] enrichCareer() frontend API function
- [x] Parallel O*NET + Haiku fetch via Promise.allSettled (graceful degradation)
- [x] MatchScoreBadge — 4-tier color coding
- [x] Enrichment panel in DETAIL phase
- [x] Stale-click race guard (latestClickRef pattern)
- [x] strip_tags on all LLM string outputs
- [x] 10 new tests (163 → 173 passing)

## Start Next Session With

> "Let's tackle the remaining deploy blockers before EC2. Confirm 173 backend
> tests pass locally, then work through in order: (1) decide the `ResumeChatView`
> `is_finalized` contract — DATA_CONTRACT says 409, code returns 200, test
> asserts 200, need a design decision not just a code change. (2) Throttle UX
> audit — review `DEFAULT_THROTTLE_RATES` for prod values, add a global 429
> handler in `apiFetch` (current DRF default 'throttled in X seconds' message
> is user-hostile). (3) Secret rotation — generate fresh `SECRET_KEY`, DB
> password, Stripe webhook signing secret before they touch EC2. (4) Only then
> walk Phase 5 EC2 deployment. Stop at any step that requires AWS console,
> DNS, Google Cloud Console, or Stripe dashboard changes and wait for explicit
> go-ahead."
