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

## Current Sprint — Phase 4: PDF Flow + Intelligent Refinement (Due April 24)

### Step 0 — Code Review & Smoke Test (do this first, before any new code)
- [ ] docker compose up --build — verify all 4 services start clean
- [ ] Run pytest — verify all 18 tests pass
- [ ] Verify GET /api/v1/resumes/ returns 200 (not 405)
- [ ] Verify POST /api/v1/translations/ works end-to-end
- [ ] Verify GET /api/v1/contacts/ returns 200 (not HTML stub)
- [ ] Code review: translate_app/services.py, context.py, views.py
- [ ] Code review: user_app/views.py (JWT hybrid pattern)
- [ ] Code review: frontend AuthContext.jsx + client.js
- [ ] Fix any issues found before starting Step 1

### Step 1 — Migration & Dependencies
- [ ] Add `is_finalized = BooleanField(default=False)` to Resume model
- [ ] Add `blank=True` to `job_description`, `civilian_title`, `summary` on Resume model
- [ ] Run makemigrations + migrate
- [ ] Add `pymupdf==1.24.11` to requirements.txt
- [ ] Rebuild Docker image (docker compose up --build)

### Step 2 — PDF Upload Endpoint
- [ ] Build `POST /api/v1/resumes/upload/` view
  - Accepts multipart/form-data with resume_file
  - Validates PDF MIME type server-side
  - Extracts text via PyMuPDF (fitz)
  - Creates Resume record (military_text, user)
  - Returns {id, military_text_preview}
- [ ] Register URL in resume_urls.py
- [ ] Update ResumeSerializer to handle partial state (blank fields)
- [ ] Smoke test with Calvin's PDF

### Step 3 — Draft Endpoint
- [ ] Expand MilitaryTranslation Pydantic schema:
  - Add `clarifying_questions: list[str]`
  - Add `assistant_reply: str`
- [ ] Update system prompt to instruct Claude to generate 2-3 clarifying questions
- [ ] Build `POST /api/v1/resumes/{id}/draft/` view
  - Accepts {job_description}
  - Loads Resume by id + user
  - Calls compress_session_anchor(military_text, job_description)
  - Saves job_description, session_anchor, civilian_title, summary, bullets
  - Returns full MilitaryTranslation
- [ ] Register URL in resume_urls.py
- [ ] Update existing tests to cover new schema fields

### Step 4 — Chat Endpoint
- [ ] Build `POST /api/v1/resumes/{id}/chat/` view
  - Accepts {message, history[]}
  - Loads Resume.session_anchor from DB
  - Builds messages: system_prompt + anchor + history + message
  - Calls Claude API
  - Updates Resume: civilian_title, summary, bullets
  - Returns updated MilitaryTranslation (clarifying_questions=[], assistant_reply populated)
- [ ] Register URL in resume_urls.py
- [ ] Handle 409 if is_finalized=True
- [ ] Write pytest tests for chat endpoint

### Step 5 — Finalize Endpoint
- [ ] Build `PATCH /api/v1/resumes/{id}/finalize/` view
  - Accepts optional {civilian_title, summary, bullets}
  - Saves provided fields + sets is_finalized=True
  - Returns finalized Resume
- [ ] Register URL in resume_urls.py
- [ ] Write pytest test for finalize endpoint

### Step 6 — Frontend: Split-Pane Translator
- [ ] Replace TranslateForm textarea with PDF dropzone (file input, PDF only)
- [ ] Implement frontend status state machine:
  - IDLE → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE
- [ ] Build split-pane layout (draft left, chat right)
- [ ] Left pane: render civilian_title, summary, bullets (editable in FINALIZING state)
- [ ] Right pane: render chat messages (clarifying_questions as assistant messages)
- [ ] Wire "Generate Draft" button → POST /{id}/draft/
- [ ] Wire chat input → POST /{id}/chat/ with history payload
- [ ] Wire "Approve & Finalize" button → FINALIZING state
- [ ] Wire "Confirm Final" button → PATCH /{id}/finalize/
- [ ] Update api/translations.js with new endpoint functions
- [ ] Update Dashboard to show is_finalized badge

### Step 7 — End-to-End Smoke Test
- [ ] Upload Calvin's PDF
- [ ] Paste a real job description
- [ ] Verify draft + 2-3 questions returned
- [ ] Answer questions in chat, verify draft updates
- [ ] Inline-edit a bullet
- [ ] Finalize and verify is_finalized=True on dashboard

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
> "Let's continue RankToRole — code review and smoke test before Phase 4. Work through TASKS.md Step 0 first, fix anything broken, then we start the migration."