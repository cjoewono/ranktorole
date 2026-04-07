# RankToRole — Military-to-Civilian Resume Translator
 
AI-powered full-stack web application that helps veterans translate military experience into civilian resumes tailored to specific job descriptions.
 
## Project Overview
 
RankToRole accepts a veteran's military background and a target job description, then uses the Claude API to generate a tailored civilian resume — including a professional title, summary, and achievement-based bullet points.
 
Built as a full-stack MVP with a focus on security, clean architecture, and production-ready deployment.
 
**Deadline:** April 24, 2026
 
---
 
## Tech Stack
 
| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, React Router DOM |
| Backend | Django REST Framework, Python 3.12 |
| Database | PostgreSQL 16 |
| AI | Claude API (claude-sonnet-4-20250514) |
| Auth | JWT (SimpleJWT) + Google OAuth 2.0 |
| Public API | O*NET Web Services (no key required) |
| Infrastructure | Docker Compose, Nginx |
| Deployment | AWS EC2 |
 
---
 
## Features
 
- JWT authentication with Google OAuth 2.0
- Military-to-civilian resume translation via Claude API
- Job-description-aware output tailored to target role
- Context window management — session anchor compression keeps API calls ≤ 5,000 tokens
- Resume history — save, view, update, delete translations
- Networking contacts manager (full CRUD)
- O*NET integration for MOS code to civilian job title mapping
- Lazy-loaded React components
- RESTful API with UUIDv4 primary keys throughout
 
---
 
## Architecture
 
```
ranktorole/
  frontend/          # React 18 + Vite + Tailwind
    src/
      api/           # fetch wrapper, auth, translations, contacts
      components/    # NavBar, TranslateForm, ResumeOutput, ProtectedRoute
      context/       # AuthContext (hybrid JWT — memory + httpOnly cookie)
      pages/         # Login, Register, Dashboard, Translator, Contacts
  backend/           # Django REST Framework
    config/          # settings, urls, wsgi, asgi
    user_app/        # Custom user model + JWT auth + Google OAuth
    translate_app/   # Claude API integration + context window management
      context.py     # DecisionsLog, RollingChatWindow
      services.py    # compress_session_anchor, build_messages, call_claude
    contact_app/     # Networking contacts CRUD
    onet_app/        # O*NET server-side proxy
  nginx/             # Reverse proxy config
  .claude/           # Claude Code configuration (local only)
```
 
### Service Map
 
| Service | Dev | Production |
|---|---|---|
| Frontend | localhost:5173 (Vite on host) | Nginx :80 |
| Backend | localhost:8000 (Docker) | Nginx :80/api/ |
| Database | localhost:5432 (Docker) | Internal only |
| Nginx | — | :80 |
 
### Dev vs Production
 
**Development:**
- Frontend runs on host via `npm run dev` (HMR enabled)
- Backend + DB run in Docker
- Vite proxies `/api/` to localhost:8000
- No Nginx needed in dev
 
**Production:**
- `npm run build` → dist/
- `docker compose up --build`
- Nginx serves dist/ and proxies `/api/` → backend
 
---
 
## Local Development Setup
 
### Prerequisites
- Docker + Docker Compose
- Node.js v18+
 
### 1. Clone the repo
```bash
git clone https://github.com/cjoewono/ranktorole.git
cd ranktorole
```
 
### 2. Configure environment
```bash
cp .env.example .env
# Fill in your values in .env
```
 
Required environment variables:
```
DEBUG=True
SECRET_KEY=
DATABASE_URL=postgresql://postgres:postgres@db:5432/ranktorole
ANTHROPIC_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
CORS_ALLOWED_ORIGINS=http://localhost:5173
JWT_SECRET_KEY=
POSTGRES_DB=ranktorole
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```
 
### 3. Start the full stack
```bash
docker compose up --build
```
 
### 4. Run migrations (first time only)
```bash
docker compose exec backend python manage.py migrate
```
 
### 5. Frontend dev server (optional — for HMR)
```bash
cd frontend
npm install
npm run dev
```
 
Visit http://localhost (production stack) or http://localhost:5173 (dev with HMR)
 
---
 
## Key Commands
 
### Docker
```bash
docker compose up              # Start all services
docker compose up --build      # Rebuild and start
docker compose stop            # Stop (preserves data)
docker compose logs -f backend # View backend logs
```
 
### Backend
```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py createsuperuser
docker compose exec backend pytest
```
 
### Frontend
```bash
cd frontend
npm run dev      # Development server
npm run build    # Production build
```
 
---
 
## API Endpoints
 
### Authentication
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | /api/v1/auth/register/ | Register new user | No |
| POST | /api/v1/auth/login/ | Login, returns tokens | No |
| POST | /api/v1/auth/refresh/ | Rotate access token | No |
| POST | /api/v1/auth/logout/ | Blacklist refresh token | Yes |
| GET | /api/v1/auth/google/ | Google OAuth redirect | No |
| POST | /api/v1/auth/google/callback/ | OAuth callback | No |
 
### Translations
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | /api/v1/translations/ | Translate military experience | Yes |
| GET | /api/v1/resumes/ | List user's translations | Yes |
| GET | /api/v1/resumes/{id}/ | Get single translation | Yes |
 
### Contacts
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | /api/v1/contacts/ | List contacts | Yes |
| POST | /api/v1/contacts/ | Create contact | Yes |
| PUT | /api/v1/contacts/{id}/ | Update contact | Yes |
| DELETE | /api/v1/contacts/{id}/ | Delete contact | Yes |
 
### Public API
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | /api/v1/onet/search/?code={mos} | MOS to civilian title | Yes |
 
---
 
## Data Models
 
### Resume
```
id               UUIDv4 PK
user             FK → User
military_text    TextField
job_description  TextField
session_anchor   JSONField (compressed JD + resume, set once)
approved_bullets JSONField
rejected_bullets JSONField
civilian_title   CharField
summary          TextField
bullets          JSONField (list of strings)
created_at       auto
updated_at       auto
```
 
### Contact
```
id        UUIDv4 PK
user      FK → User
name      CharField
email     EmailField
company   CharField
role      CharField
notes     TextField
created_at auto
updated_at auto
```
 
---
 
## Security
 
- JWT access tokens (15 min expiry, stored in memory only)
- JWT refresh tokens (7 days, httpOnly cookie — JS cannot read)
- Silent token rehydration on page load via httpOnly cookie
- Google OAuth 2.0 for social login
- All endpoints require authentication except `/api/v1/auth/`
- All queries scoped to `request.user`
- No PII in server logs
- CORS restricted to frontend URL only
- PostgreSQL not exposed externally
- Secrets managed via `.env` (never committed)
 
See `SECURITY.md` for full security documentation.
 
---
 
## Context Window Management
 
The translation service uses a four-layer context model to keep Claude API calls efficient:
 
| Layer | Content | Budget | Policy |
|---|---|---|---|
| 1 | System prompt | ~400 tokens | Static |
| 2 | Session anchor (compressed JD + resume) | ~700 tokens | Set once, always kept |
| 3 | Decisions log | ~100/bullet | Never pruned |
| 4 | Rolling chat window | ≤ 2,000 tokens | Pruned oldest first |
 
**Target: ≤ 5,000 tokens per API call.** See `ARCHITECTURE.md` for full design.
 
---
 
## Development Approach
 
Built using Claude Code subagent orchestration across 7 specialized agents:
 
| Agent | Scope |
|---|---|
| scaffold-agent | Django project init + Vite scaffold |
| models-agent | All models, serializers, migrations |
| auth-agent | JWT + Google OAuth |
| translate-agent | Claude API integration + context management |
| auth-fix-agent | Hybrid JWT security pattern |
| frontend-agent | React Router, all pages and components |
| deploy-agent | Docker Compose, Dockerfile, Nginx |
 
---
 
## Project Status
 
| Area | Status |
|---|---|
| Project scaffolding | ✅ Complete |
| Claude Code configuration | ✅ Complete |
| Context window management | ✅ Complete |
| Subagent orchestration setup | ✅ Complete |
| Docker Compose + Nginx | ✅ Complete |
| Django project init | ✅ Complete |
| Authentication (JWT + Google OAuth) | ✅ Complete |
| Translation service (Claude API) | ✅ Complete |
| Frontend (React + Tailwind) | ✅ Complete |
| Migrations applied + verified | ✅ Complete |
| Deployment (EC2) | ⬜ Not started |
 
*Last updated: April 6, 2026 — Phase 3 complete, full stack running locally*
 
---
 
## Author
 
Calvin Joewono — [github.com/cjoewono](https://github.com/cjoewono)