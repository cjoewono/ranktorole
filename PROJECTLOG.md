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

**Start next session with:**

> "Let's continue RankToRole — implement the PDF flow. Start with the migration and requirements, then the upload endpoint."

---

Project log maintained: github.com/cjoewono/ranktorole
Last updated: April 6, 2026 — Session 03 design complete, implementation ready

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

### Next Session

UI/UX improvements before EC2 deployment.
EC2 deployment pushed to Phase 5 (after UI/UX work complete).

## Session 05 — UI/UX Overhaul + Phase D Complete

Date: April 9, 2026 | Status: ✅ Complete

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
| --------------------------------- | ----------------------------------------------------------------------- | --- | ----------------------- |
| draft.roles.map() crash on render | Null guards added across DraftPane + ChatPane                           |
| Edit & Export loading blank IDLE  | resumeId: resume.id                                                     |     | id fix in RESUME_LOADED |
| Sticky chat pane not working      | SplitPane overflow:hidden + height:100% on right pane                   |
| Export PDF button missing         | Rewrote exportPDF() with jsPDF, button at top-right of FinalizingEditor |
| Single question schema            | clarifying_questions: list[str] → clarifying_question: str              |
| Stale build cache                 | docker compose stop + rebuild cleared crash                             |

### Next Session

- Minor visual tweaks (spacing, typography)
- EC2 deployment (Phase 4 from original plan)
- Update DATA_CONTRACT.md to reflect roles[] + DB-backed chat history

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

Project log maintained: github.com/cjoewono/ranktorole
Last updated: April 13, 2026 — Security hardening complete

---

## April 12, 2026 | Task 6 | Tiered Throttle System

**Status:** ✅ Complete

- Apr 12: Implemented tiered throttle system — User.tier field (free/pro), TieredThrottle base class, 5 throttle subclasses, TIERED_THROTTLE_RATES settings, 20 new tests (64→84 total)

---

## April 13, 2026 | Session — HTTPS/SSL + Production Deployment Prep

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

Project log maintained: github.com/cjoewono/ranktorole
Last updated: April 13, 2026 — Career Recon feature complete, 108 tests passing

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

## April 13, 2026 | O*NET v2 API Migration

**Status:** ✅ Complete

### Summary

Migrated all three O*NET proxy views from the public `services.onetcenter.org/ws` endpoint to the authenticated v2 API at `api-v2.onetcenter.org`. Auth uses `X-API-Key` header sourced from `ONET_API_KEY` env var. No endpoint path changes — all routes and response shapes unchanged.

### Changes

| File | Action | Detail |
|------|--------|--------|
| `config/settings.py` | Modified | Added `ONET_API_KEY` from env |
| `onet_app/views.py` | Modified | New base URL, shared `_onet_headers()` helper, all requests now send `X-API-Key` |
| `onet_app/tests.py` | Modified | Added 3 tests verifying API key header is sent |
| `.env.example` | Modified | Added `ONET_API_KEY` |
| Docs | Modified | CLAUDE.md, ARCHITECTURE.md, SECURITY.md, PROJECTLOG.md updated |

### Follow-up: v2 Response Shape Fix

Fixed field name mismatches between v1 and v2 API responses:

- `military_matches.match` → `military_match` (top-level flat array)
- Overview `description` → `what_they_do` (v2 uses different field name)
- Skills/knowledge: v2 returns a list of categories with sub-`element` arrays (not `{"element": [...]}` dict)
- Technology: v2 returns list directly; category `title` is a plain string (not `{"name": "..."}`); examples use `title` key (not `name`)
- Outlook sub-endpoint: `outlook` → `job_outlook`
- Updated test mocks to use v2 field shapes
- Tests: 115/115 passing
