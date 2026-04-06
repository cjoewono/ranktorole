# TASKS.md

## Status Key
- [ ] Not started
- [~] In progress
- [x] Done
- [!] Blocked

## Current Sprint (Due April 24)

### Infrastructure
- [ ] Initialize Django project + app structure
- [ ] Initialize React + Vite + Tailwind
- [ ] Write docker-compose.yml (frontend, backend, db, nginx)
- [ ] Write Nginx config
- [ ] Configure .env and .env.example
- [ ] Verify full stack boots via docker compose up --build

### Authentication
- [ ] Install and configure djangorestframework-simplejwt
- [ ] Build /api/v1/auth/register/ endpoint
- [ ] Build /api/v1/auth/login/ endpoint (returns access + refresh tokens)
- [ ] Build /api/v1/auth/refresh/ endpoint
- [ ] Apply JWT middleware to all non-auth endpoints
- [ ] Build frontend login/register forms
- [ ] Store JWT in httpOnly cookie on frontend
- [ ] Protect all frontend routes (redirect to login if no token)
- [ ] Install social-auth-app-django
- [ ] Configure Google OAuth credentials in .env
- [ ] Build /api/v1/auth/google/ endpoint
- [ ] Frontend Google login button

### Database Models
- [ ] User model (UUID PK, extend AbstractUser)
- [ ] Resume model (UUID PK, user FK, military_text, job_description, output JSON, created_at)
- [ ] Run and verify migrations

### Translation Service
- [ ] Create translate_app Django app
- [ ] Build MilitaryTranslation Pydantic schema
- [ ] Build translation_service.py (Claude API call)
- [ ] Build POST /api/v1/translate/ view
- [ ] Write pytest tests for translation_service.py

### Frontend
- [ ] Build layout + navigation (React Router DOM)
- [ ] Build TranslateForm component (military_text + job_description inputs)
- [ ] Build ResumeOutput component (displays civilian_title, summary, bullets)
- [ ] Build resume history page (list saved resumes)
- [ ] Lazy load ResumeOutput component
- [ ] Connect all forms to backend API via relative paths

### Public API (O*NET)
- [ ] Create onet_app Django app
- [ ] Build server-side proxy view
- [ ] Build GET /api/v1/onet/search/ endpoint
- [ ] Connect to frontend MOS code input field

### Deployment
- [ ] Provision EC2 instance
- [ ] Install Docker + Docker Compose on EC2
- [ ] Configure production .env on EC2
- [ ] Set up IAM instance role (no hardcoded credentials)
- [ ] Open ports 80/443 only in security group
- [ ] Deploy via docker compose up --build -d
- [ ] Smoke test all endpoints on live URL

## Blocked
None

## Completed
None