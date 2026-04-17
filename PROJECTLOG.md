RankToRole — Project Log

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

1. DNS: Point `cjoewono.com` and `www.cjoewono.com` A records to EC2 public IP
2. EC2 security group: Confirm ports 80/443 open, 22 from your IP only, no 8000/5432
3. Install Docker on EC2 if not already installed
4. Install Certbot on EC2: `sudo apt install certbot`
5. Create production `.env` on EC2 with `DEBUG=False`, rotated `SECRET_KEY`, real DB password, production `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `GOOGLE_OAUTH_REDIRECT_URI=https://cjoewono.com/auth/google/callback`
6. Google Cloud Console: Add `https://cjoewono.com/auth/google/callback` as authorized redirect URI
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

1. DNS A records for `cjoewono.com` and `www.cjoewono.com` → EC2 public IP
2. Security group: ports 80/443 open to world; 22 from admin IP; no 8000 or 5432
3. `apt install docker.io docker-compose-plugin certbot`
4. Production `.env` on host with `DEBUG=False`, rotated `SECRET_KEY`, real DB password
5. `sudo certbot certonly --standalone -d cjoewono.com -d www.cjoewono.com`
6. Google Cloud Console — add `https://cjoewono.com/auth/google/callback` as authorized redirect
7. Stripe dashboard — live webhook endpoint pointed at `https://cjoewono.com/api/v1/billing/webhook/`, signing secret copied into `.env`
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

- 7 endpoint tests: auth, profile gate, invalid code, O*NET 404, Haiku failure (503), happy path, unauthenticated
- 3 cost-control tests: cache hit skips LLM, profile change invalidates cache, global ceiling blocks call
- Final: 163 → 173 passing

### Cost Model

| Tier | Max/day | Max cost/day |
|------|---------|-------------|
| Free | 15 calls | $0.04 |
| Pro  | 25 calls | $0.065 |
| Global ceiling | 500 calls | $1.30 |

Expected monthly spend at 100 pro users / 10 sessions: ~$3/month (60-75% cache hit rate).

---

Project log maintained: github.com/cjoewono/ranktorole
Last updated: April 17, 2026 — Session 13 (Career Recon Enrichment), 173 tests passing
