RankToRole — Military-to-Civilian Resume Translator

AI-powered full-stack web application that helps veterans translate military experience into civilian resumes tailored to specific job descriptions.


Project Overview
RankToRole accepts a veteran's military background and a target job description, then uses the Claude API to generate a tailored civilian resume — including a professional title, summary, and achievement-based bullet points.
Built as a full-stack MVP with a focus on security, clean architecture, and production-ready deployment.
Deadline: April 24, 2026

Tech Stack
LayerTechnologyFrontendReact 18, Vite, Tailwind CSS, React Router DOMBackendDjango REST Framework, PythonDatabasePostgreSQLAIClaude API (claude-sonnet-4-20250514)AuthJWT (SimpleJWT) + Google OAuth 2.0Public APIO*NET Web Services (no key required)InfrastructureDocker Compose, NginxDeploymentAWS EC2

Features

JWT authentication with Google OAuth 2.0
Military-to-civilian resume translation via Claude API
Job-description-aware output tailored to target role
Resume history — save, view, update, delete translations
Networking contacts manager (full CRUD)
O*NET integration for MOS code to civilian job title mapping
Lazy-loaded React components
RESTful API with UUIDv4 primary keys throughout


Architecture
ranktorole/
  frontend/        # React 18 + Vite + Tailwind
  backend/         # Django REST Framework
    user_app/      # Custom user model + JWT auth
    resume_app/    # Translation model + CRUD
    contact_app/   # Networking contacts
    translate_app/ # Claude API integration
    onet_app/      # O*NET proxy
    services/      # translation_service.py
  nginx/           # Reverse proxy config
  .claude/         # Claude Code skill files (local only)
Service Map
ServiceDevProductionFrontendlocalhost:5173 (Vite on host)Nginx :80Backendlocalhost:8000 (Docker)Nginx :80/api/Databaselocalhost:5432 (Docker)Internal onlyNginx—:80
Dev vs Production
Development:

Frontend runs on host via npm run dev (HMR enabled)
Backend + DB run in Docker
Vite proxies /api/ to localhost:8000
No Nginx needed in dev

Production:

npm run build → dist/
docker compose up --build
Nginx serves dist/ and proxies /api/ → backend


Local Development Setup
Prerequisites

Docker + Docker Compose
Node.js v18+
Python 3.11+

1. Clone the repo
bashgit clone https://github.com/cjoewono/ranktorole.git
cd ranktorole
2. Configure environment
bashcp .env.example .env
# Fill in your values in .env
Required environment variables:
DEBUG=True
SECRET_KEY=
DATABASE_URL=postgresql://postgres:postgres@db:5432/ranktorole
ANTHROPIC_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
CORS_ALLOWED_ORIGINS=http://localhost:5173
JWT_SECRET_KEY=
3. Start backend services
bashdocker compose up --build
4. Start frontend
bashcd frontend
npm install
npm run dev
Visit http://localhost:5173

Key Commands
Docker
bashdocker compose up              # Start all services
docker compose up --build      # Rebuild and start
docker compose stop            # Stop (preserves data)
docker compose logs -f backend # View backend logs
Backend
bashdocker compose exec backend python manage.py migrate
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py createsuperuser
docker compose exec backend pytest
Frontend
bashcd frontend
npm run dev      # Development server
npm run build    # Production build

API Endpoints
Authentication
MethodEndpointDescriptionAuthPOST/api/v1/auth/register/Register new userNoPOST/api/v1/auth/login/Login, returns tokensNoPOST/api/v1/auth/refresh/Rotate access tokenNoPOST/api/v1/auth/logout/Blacklist refresh tokenYesGET/api/v1/auth/google/Google OAuth redirectNoPOST/api/v1/auth/google/callback/OAuth callbackNo
Translations
MethodEndpointDescriptionAuthPOST/api/v1/translations/Translate military experienceYesGET/api/v1/translations/List user's translationsYesGET/api/v1/translations/{id}/Get single translationYesPUT/api/v1/translations/{id}/Update translationYesDELETE/api/v1/translations/{id}/Delete translationYes
Contacts
MethodEndpointDescriptionAuthGET/api/v1/contacts/List contactsYesPOST/api/v1/contacts/Create contactYesPUT/api/v1/contacts/{id}/Update contactYesDELETE/api/v1/contacts/{id}/Delete contactYes
Public API
MethodEndpointDescriptionAuthGET/api/v1/onet/search/?code={mos}MOS to civilian titleYes

Data Models
Resume
id            UUIDv4 PK
user          FK → User
military_text TextField
job_description TextField
civilian_title CharField
summary       TextField
bullets       JSONField (list of strings)
created_at    auto
updated_at    auto
Contact
id            UUIDv4 PK
user          FK → User
name          CharField
email         EmailField
company       CharField
role          CharField
notes         TextField
created_at    auto
updated_at    auto

Security

JWT access tokens (15 min expiry)
JWT refresh tokens (7 days, httpOnly cookie)
Google OAuth 2.0 for social login
All endpoints require authentication except /api/v1/auth/
All queries scoped to request.user
No PII in server logs
CORS restricted to frontend URL only
PostgreSQL not exposed externally
Secrets managed via .env (never committed)

See SECURITY.md for full security documentation.

Development Approach
This project was built using Claude Code for AI-assisted development. Project architecture, security design, and all engineering decisions were planned and validated before implementation began.
Key planning documents:

CLAUDE.md — Claude Code configuration and project rules
ARCHITECTURE.md — System design and Docker patterns
SECURITY.md — Security rules and hardening
DATA_CONTRACT.md — API input/output contracts
TASKS.md — Development task tracker


Project Status
AreaStatusProject scaffolding✅ CompleteClaude Code configuration✅ CompleteDocker Compose setup⬜ Not startedDjango project init⬜ Not startedAuthentication⬜ Not startedTranslation service⬜ Not startedFrontend⬜ Not startedDeployment⬜ Not started
Last updated: April 6, 2026 — Phase 1 complete

Author
Calvin Joewono — github.com/cjoewono