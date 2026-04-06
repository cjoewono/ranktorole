# Military-to-Civilian Resume Translator

## Stack
React 18 (Vite) | Django REST Framework | PostgreSQL | Docker Compose | Nginx

## Deadline
April 24, 2026

## Service Map
- Frontend: Vite internal :5173 → Nginx :80
- Backend: Django internal :8000 → Nginx :80/api/
- Database: PostgreSQL :5432, service name: db
- Nginx: proxies /api/ → backend, / → frontend

## Key Commands
### Docker
- `docker compose up` / `docker compose up --build` / `docker compose stop`
- `docker compose logs -f [frontend|backend|db]`

### Backend
- `docker compose exec backend python manage.py migrate`
- `docker compose exec backend python manage.py makemigrations`
- `docker compose exec backend pytest`

### Frontend
- `docker compose exec frontend npm run build`

## Architecture
See ARCHITECTURE.md for system design patterns and Docker lessons.

## LLM Integration
- Provider: Claude API (claude-sonnet-4-20250514)
- Location: backend/services/translation_service.py
- Input: {military_text (string), job_description (string)}
- Output: JSON {civilian_title, summary, bullets[]}
- Env var: ANTHROPIC_API_KEY
- SDK: anthropic (pip install anthropic)

## Conventions
### Python/Django
- PEP 8, explicit imports
- Thin views; all logic in services.py
- Serializers for all data transformations
- All models use UUIDv4 primary keys

### React
- Functional components + Hooks
- Tailwind for all styling
- React Router DOM for navigation
- Lazy load heavy components

### API
- RESTful: pluralized nouns, e.g. /api/v1/resumes/
- JWT auth on all endpoints except /api/v1/auth/

## Public API (no key)
- O*NET Web Services: https://services.onetcenter.org/ws/
- Purpose: map military occupation codes to civilian job titles
- Server-side proxy only, never call from frontend
- Endpoint: GET /api/v1/onet/search/?code={mos_code}

## OAuth
- Provider: Google OAuth 2.0
- Library: social-auth-app-django
- Purpose: satisfies "secret key with OAuth" requirement
- Env vars: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
- Endpoint: /api/v1/auth/google/

## Hard Rules
- Do not add packages without asking
- Do not change model field names
- Do not run docker compose down (use stop)
- Do not modify docker-compose.yml or .env without instruction
- Do not create new Django apps without confirming name
- See SECURITY.md before touching auth, API keys, or user data
- Check TASKS.md before starting any work
- User layer files (.env, docker-compose.yml, migrations/) are read-only unless explicitly told otherwise