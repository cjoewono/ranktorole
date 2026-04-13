# TASKS.md

## Status Key

- [ ] Not started
- [~] In progress
- [x] Done
- [!] Blocked

---

## Completed — Phases 1–3 (Session 01–02)

### Infrastructure

- [x] Initialize Django project + app structure
- [x] Initialize React + Vite + Tailwind
- [x] Write docker-compose.yml (frontend, backend, db, nginx)
- [x] Write Nginx config
- [x] Configure .env and .env.example
- [x] Verify full stack boots via docker compose up --build

### Authentication

- [x] Install and configure djangorestframework-simplejwt
- [x] Build /api/v1/auth/register/ endpoint
- [x] Build /api/v1/auth/login/ endpoint (returns access + refresh tokens)
- [x] Build /api/v1/auth/refresh/ endpoint
- [x] Build /api/v1/auth/logout/ endpoint
- [x] Apply JWT middleware to all non-auth endpoints
- [x] Build frontend login/register forms
- [x] Hybrid JWT: access token in memory, refresh token in httpOnly cookie
- [x] Protect all frontend routes (redirect to login if no token)
- [x] Install social-auth-app-django
- [x] Configure Google OAuth credentials in .env
- [x] Build /api/v1/auth/google/ endpoint
- [x] Frontend Google login button

### Database Models

- [x] User model (UUID PK, extend AbstractUser)
- [x] Resume model (UUID PK, user FK, military_text, job_description, session_anchor, approved_bullets, rejected_bullets, output JSON, created_at)
- [x] Contact model (UUID PK, user FK, name, email, company, role, notes)
- [x] Run and verify migrations

### Translation Service (original single-shot — superseded by Phase 4)

- [x] Create translate_app Django app
- [x] Write context.py — DecisionsLog, RollingChatWindow
- [x] Write compress_session_anchor() and build_messages() in services.py
- [x] Build MilitaryTranslation Pydantic schema
- [x] Build POST /api/v1/translations/ view
- [x] Write pytest tests for context.py and services.py

### Frontend (original)

- [x] Build layout + navigation (React Router DOM)
- [x] Build TranslateForm component (military_text + job_description inputs)
- [x] Build ResumeOutput component (displays civilian_title, summary, bullets)
- [x] Build resume history page (list saved resumes)
- [x] Lazy load components
- [x] Connect all forms to backend API via relative paths

### Contacts CRUD

- [x] Build contact_app views (list, create, update, delete)
- [x] Connect frontend Contacts page to API

---

### Completed — Session 08 (April 11)

- [x] Code review fixes — fetchOnetSkills crash, ProtectedRoute removal,
      profile gate in AppShell, \_build_profile_block DRY helper,
      dead call_claude removal, Anthropic client singleton,
      throttles on FinalizeView + OnetSearchView, ErrorBoundary,
      legacy dead code purge (TranslationView, translations.js, context.py)

### Completed — Tiered Throttle (April 12)

- [x] User.tier field (free/pro) + migration 0004
- [x] TieredThrottle base class + 5 subclasses in throttles.py
- [x] TIERED_THROTTLE_RATES in settings.py
- [x] 20 throttle tests added

### Completed — HTTPS/SSL Deployment Prep (April 13)

- [x] settings.py HSTS fix + CSRF_TRUSTED_ORIGINS
- [x] nginx/default.conf SSL termination rewrite
- [x] docker-compose.yml port 443 + cert volumes
- [x] .env.example expanded with all production vars

### Completed — Security Hardening (April 13)

- [x] Input validation: JD 10-15k, chat 2k, finalize field limits, contact limits
- [x] RegisterThrottle (5/hour)
- [x] Login/register error normalization (anti-enumeration)
- [x] strip_tags on AI output
- [x] get_user_resume helper extracted
- [x] Type hints on all view methods
- [x] Docstrings on all services.py functions
- [x] 13 new tests (97 total)

---

## Current Sprint — Phase 4: PDF Flow + Intelligent Refinement (Due April 24)

### Step 0 — Code Review & Smoke Test (do this first, before any new code)

- [x] docker compose up --build — verify all 4 services start clean
- [x] Run pytest — verify all tests pass (49 passing as of Apr 9)
- [x] Verify GET /api/v1/resumes/ returns 200 (not 405)
- [x] Verify POST /api/v1/translations/ works end-to-end
- [x] Verify GET /api/v1/contacts/ returns 200 (not HTML stub)
- [x] Code review: translate_app/services.py, context.py, views.py
- [x] Code review: user_app/views.py (JWT hybrid pattern)
- [x] Code review: frontend AuthContext.jsx + client.js
- [x] Fix any issues found before starting Step 1

### Step 1 — Migration & Dependencies

- [x] Add `is_finalized = BooleanField(default=False)` to Resume model
- [x] Run makemigrations + migrate
- [x] Add `pymupdf==1.24.11` to requirements.txt
- [x] Rebuild Docker image (docker compose up --build)

### Step 2 — PDF Upload Endpoint

- [x] Build `POST /api/v1/resumes/upload/` view
  - Accepts multipart/form-data with resume_file
  - Validates PDF MIME type server-side
  - Extracts text via PyMuPDF (fitz)
  - Creates Resume record (military_text, user)
  - Returns {id, created_at}
- [x] Register URL in resume_urls.py
- [x] Update ResumeSerializer to handle partial state (blank fields)

### Step 3 — Draft Endpoint

- [x] Expand services with DraftResponse Pydantic schema:
  - `clarifying_questions: list[str]`
  - `assistant_reply: str`
- [x] Update system prompt to instruct Claude to generate 2-3 clarifying questions
- [x] Build `POST /api/v1/resumes/{id}/draft/` view
  - Accepts {job_description}
  - Loads Resume by id + user
  - Calls call_claude_draft(military_text, job_description)
  - Saves job_description, session_anchor, civilian_title, summary, bullets
  - Returns full DraftResponse
- [x] Register URL in resume_urls.py
- [x] Tests added (TestResumeDraftView — 5 tests)

### Step 4 — Chat Endpoint

- [x] Build `POST /api/v1/resumes/{id}/chat/` view
  - Accepts {message, history[]}
  - Loads Resume.session_anchor from DB
  - Calls Claude API via call_claude_chat
  - Updates Resume: civilian_title, summary, bullets
  - Returns updated fields + assistant_reply
- [x] Register URL in resume_urls.py
- [x] Handle 409 if is_finalized=True
- [x] Write pytest tests for chat endpoint (TestResumeChatView — 6 tests)

### Step 5 — Finalize Endpoint

- [x] Build `PATCH /api/v1/resumes/{id}/finalize/` view
  - Accepts optional {civilian_title, summary, bullets}
  - Saves provided fields + sets is_finalized=True
  - Returns finalized Resume
- [x] Register URL in resume_urls.py
- [x] Write pytest tests for finalize endpoint (TestResumeFinalizeView — 6 tests)

### Step 6 — Frontend: Split-Pane Translator

- [x] PDF file input (PDF only, upload before draft)
- [x] Frontend status state machine: IDLE → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE
- [x] Split-pane layout (draft left, chat right)
- [x] Left pane: read-only draft in REVIEWING; editable in FINALIZING
- [x] Right pane: chat messages (clarifying_questions as initial assistant messages)
- [x] "Generate Draft" button → POST /{id}/draft/
- [x] Chat input → POST /{id}/chat/ with history payload
- [x] "Approve & Finalize" button → FINALIZING state
- [x] "Confirm Final" button → PATCH /{id}/finalize/
- [x] api/resumes.js with all endpoint functions
- [x] Dashboard shows is_finalized badge

### Step 7 — End-to-End Smoke Test

- [x] Upload Calvin's PDF
- [x] Paste a real job description
- [x] Verify draft + single clarifying question returned
- [x] Answer questions in chat, verify draft updates
- [x] Inline-edit a bullet
- [x] Finalize and verify is_finalized=True on dashboard

---

## Completed — Session 06 (April 10)

### API Layer Refactor (Frontend)

- [x] Add APIError class + handleResponse helper to client.js
- [x] Refactor apiFetch to return parsed data, throw APIError
- [x] Eliminate manual error handling from resumes.js, auth.js, contacts.js, translations.js
- [x] Extract exportPDF to frontend/src/utils/pdfExport.js

### Backend Service Layer

- [x] Add ChatResult dataclass to services.py
- [x] Migrate chat history management into call_claude_chat
- [x] Update ResumeChatView to consume ChatResult
- [x] Update 4 ResumeChatView tests to mock ChatResult return type
- [x] Verify 77/77 tests pass

---

## Completed — Session 07 (April 11)

### SPA Shell Refactor

- [x] Implement AppShell pattern (always-mounted NavBar, pages shown/hidden via CSS)
- [x] Add ResumeContext (frontend/src/context/ResumeContext.jsx)
- [x] Extract PageHeader shared component (frontend/src/components/PageHeader.jsx)
- [x] Refactor Dashboard to use PageHeader, remove NavBar import
- [x] Refactor Contacts to use PageHeader, remove NavBar import
- [x] Refactor ResumeBuilder to accept setFullscreen prop, handle DONE phase
- [x] Delete ProtectedRoute.jsx (dead code)
- [x] Add catch-all redirect to /dashboard for unknown paths
- [x] Verify frontend build passes, 77 backend tests pass

### Frontend Component Decomposition

- [x] Extract state machine into frontend/src/hooks/useResumeMachine.js
- [x] Reduce ResumeBuilder.jsx to JSX-only (1 hook call, no logic)
- [x] Split DraftPane.jsx into DraftPane/ directory:
  - [x] DraftPane/DiffView.jsx
  - [x] DraftPane/BulletEditor.jsx
  - [x] DraftPane/FinalizingEditor.jsx
  - [x] DraftPane/index.jsx
- [x] Delete flat DraftPane.jsx
- [x] Verify Vite builds 441 modules with 0 import errors
- [x] Verify 77/77 backend tests pass

---

## Session 10 — Career Recon

- [x] OnetMilitarySearchView: GET /api/v1/onet/military/
- [x] OnetCareerDetailView: GET /api/v1/onet/career/{code}/
- [x] onet_app/tests.py: 11 tests (108 total)
- [x] frontend/src/api/onet.js: searchMilitaryCareers, getCareerDetail
- [x] frontend/src/pages/CareerRecon.jsx: SEARCH → RESULTS → DETAIL
- [x] /recon route wired in App.jsx + NavBar.jsx

---

## Phase 5 — EC2 Deployment (after Phase 4 complete)

- [ ] Provision EC2 instance (Ubuntu 22.04)
- [ ] Install Docker + Docker Compose on EC2
- [ ] Configure production .env on EC2
- [ ] Set up IAM instance role (no hardcoded credentials)
- [ ] Open ports 80/443 only in security group
- [ ] Deploy via docker compose up --build -d
- [ ] Smoke test all endpoints on live URL

---

## Blocked

None

---

## Start Next Session With

> "Let's continue RankToRole — UI/UX redesign. Read .stitch/DESIGN.md
> first. Run pytest to confirm 97 passing, then start implementation."
