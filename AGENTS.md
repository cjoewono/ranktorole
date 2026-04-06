# AGENTS.md — RankToRole Agent Roster

## How Agents Are Used
Claude Code spawns subagents via the Task tool. Each agent gets its own
isolated context window. Agents read only the files listed under
"Context Loaded" — nothing else.

## Orchestration Entry Point
.claude/orchestrate.md — read this before spawning any agent.

---

## Phase 3A — Sequential (run in order)

### 1. scaffold-agent
Trigger: Phase 3 start — no backend or frontend code exists yet
VoltAgent base: fullstack-developer
Custom skill: none (uses CLAUDE.md + ARCHITECTURE.md directly)
Context loaded:
  - CLAUDE.md
  - ARCHITECTURE.md
  - TASKS.md
Delivers:
  - Django project initialized (config/ layout)
  - translate_app, user_app, contact_app, onet_app created
  - settings.py configured (installed apps, JWT, CORS, database)
  - Root urls.py with /api/v1/ routing
  - Empty frontend/ directory with Vite scaffold
Must not touch: docker-compose.yml, .env, any service logic

### 2. models-agent
Trigger: After scaffold-agent completes
VoltAgent base: django-developer + postgres-pro
Custom skill: .claude/skills/models.md
Context loaded:
  - .claude/skills/models.md
  - ARCHITECTURE.md § Resume Model Additions
  - DATA_CONTRACT.md
Delivers:
  - translate_app/models.py (Resume with all JSONFields)
  - user_app/models.py (User extending AbstractUser, UUID PK)
  - contact_app/models.py (Contact model)
  - Initial migrations created and verified
Must not touch: services.py, context.py, views.py, frontend/

---

## Phase 3B — Parallel (run simultaneously after 3A)

### 3. auth-agent
Trigger: After models-agent completes
VoltAgent base: django-developer
Custom skill: .claude/skills/auth.md
Context loaded:
  - .claude/skills/auth.md
  - SECURITY.md
  - DATA_CONTRACT.md § Auth Endpoints
Delivers:
  - SimpleJWT configured
  - user_app/views.py: register, login, refresh, logout
  - user_app/urls.py
  - Google OAuth via social-auth-app-django
  - JWT middleware on all non-auth endpoints
Must not touch: translate_app/, contact_app/, onet_app/, frontend/

### 4. translate-agent
Trigger: After models-agent completes (parallel with auth-agent)
VoltAgent base: django-developer + ai-engineer
Custom skill: .claude/skills/translate.md
Context loaded:
  - .claude/skills/translate.md
  - ARCHITECTURE.md § Context Window Management
  - DATA_CONTRACT.md § Translation Endpoint
Delivers:
  - translate_app/context.py (DecisionsLog, RollingChatWindow)
  - translate_app/services.py (compress_session_anchor, build_messages, call_claude)
  - translate_app/serializers.py
  - translate_app/views.py (POST /api/v1/translations/)
  - translate_app/urls.py
  - pytest tests for context.py and services.py
Must not touch: user_app/, contact_app/, frontend/, docker-compose.yml

---

## Phase 3C — Sequential (after 3B confirmed working)

### 5. frontend-agent
Trigger: After auth-agent and translate-agent both complete
VoltAgent base: react-specialist + frontend-developer
Custom skill: none (uses DATA_CONTRACT.md directly)
Context loaded:
  - DATA_CONTRACT.md (full file)
  - CLAUDE.md § Conventions (React section)
  - ARCHITECTURE.md § Dev vs Production
Delivers:
  - Vite + React 18 + Tailwind configured
  - React Router DOM: Login, Register, Dashboard, Translator, Contacts pages
  - TranslateForm component (military_text + job_description inputs)
  - ResumeOutput component (civilian_title, summary, bullets)
  - JWT auth flow (localStorage, Outlet context, protected routes)
  - All API calls use relative paths via Vite proxy
Must not touch: backend/ (any file)

### 6. deploy-agent
Trigger: After frontend-agent completes
VoltAgent base: docker-expert
Custom skill: .claude/skills/deploy.md
Context loaded:
  - .claude/skills/deploy.md
  - ARCHITECTURE.md § Docker/Nginx Pattern
  - ARCHITECTURE.md § Dev vs Production
Delivers:
  - docker-compose.yml (backend, db, nginx + named postgres volume)
  - nginx/default.conf (/ → frontend dist, /api/ → backend:8000)
  - backend/Dockerfile (python:3.12-slim, runserver dev / gunicorn prod)
  - Verified: docker compose up --build boots all services
Must not touch: backend/translate_app/, backend/user_app/, frontend/src/

---

## Summary Report Format
After all agents complete, orchestrator delivers:

1. Agent completion status (pass/fail per agent)
2. Files created (count by agent)
3. Tests passed/failed
4. Endpoints verified (list)
5. Any blocked items requiring manual intervention