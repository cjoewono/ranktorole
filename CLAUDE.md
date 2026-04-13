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

### Production (EC2)

- `sudo certbot certonly --webroot -w /var/lib/letsencrypt -d cjoewono.com -d www.cjoewono.com`
- `docker compose up -d db nginx frontend`
- `docker compose run -d backend gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3`
- `docker compose exec backend python manage.py migrate`
- `sudo crontab -e` → add `0 */12 * * * certbot renew --quiet && docker compose -f /path/to/docker-compose.yml exec nginx nginx -s reload`

## Architecture

See ARCHITECTURE.md for system design patterns and Docker lessons.

## Product Flow

1. User uploads PDF resume → backend extracts text, creates Resume record, returns resume_id
2. User pastes job description → single LLM call returns draft + 2-3 clarifying questions
3. User answers questions in chat → stateful refinement turns (history persisted to DB, loaded server-side)
4. User approves → inline bullet editing → "Approve & Finalize" → is_finalized = True

## LLM Integration

- Provider: Claude API (claude-sonnet-4-20250514)
- Location: backend/translate_app/services.py
- Input call 1: {military_text (string), job_description (string)}
- Input call 2+: {session_anchor (dict from DB), chat_history (list from DB), message (string)}
- Output every call: JSON matching MilitaryTranslation schema (see below)
- Env var: ANTHROPIC_API_KEY
- SDK: anthropic (pip install anthropic)

## Pydantic Schema (MilitaryTranslation)

```python
class RoleEntry(BaseModel):
    title: str
    org: str
    dates: str
    bullets: list[str]

class MilitaryTranslation(BaseModel):
    civilian_title: str
    summary: str
    roles: list[RoleEntry]
    clarifying_question: str   # single question on draft call, "" on chat turns
    assistant_reply: str       # "" on draft call, populated on chat turns
```

## URL Map

```
POST   /api/v1/resumes/upload/          PDF → military_text, returns resume_id
POST   /api/v1/resumes/{id}/draft/      JD → draft + questions, sets session_anchor
POST   /api/v1/resumes/{id}/chat/       message → updated draft + reply (history loaded from DB)
PATCH  /api/v1/resumes/{id}/finalize/   final edits → is_finalized=True
GET    /api/v1/resumes/                 list resumes for authenticated user
GET    /api/v1/resumes/{id}/            retrieve single resume
DELETE /api/v1/resumes/{id}/            delete resume
GET    /api/v1/onet/military/            MOS search → civilian career matches (Veterans API)
GET    /api/v1/onet/career/{code}/       career detail aggregation (skills, knowledge, salary, outlook)
```

## Context Window Budget (per call)

| Layer            | Tokens     | Policy                               |
| ---------------- | ---------- | ------------------------------------ |
| System prompt    | ~400       | Static — never changes               |
| Session anchor   | ~350       | Set once on draft call, always kept  |
| DB chat history  | ≤ 500      | Loaded from DB, appended server-side |
| New user message | ~100       | Current turn only                    |
| **Total input**  | **~1,350** | Well under 5,000 token budget        |

Raw military_text and job_description are NEVER passed after call 1.

## Cost Reference

- ~$0.016 per draft call (call 1)
- ~$0.013 per refinement turn
- ~$0.055 per full session (call 1 + 3 turns)
- ~$0.025–$0.035 with prompt caching

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
- Frontend state machine: IDLE → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE

### API

- RESTful: pluralized nouns, e.g. /api/v1/resumes/
- JWT auth on all endpoints except /api/v1/auth/
- multipart/form-data on upload endpoint only; JSON everywhere else

## O\*NET API (authenticated v2)

- O\*NET v2 API: https://api-v2.onetcenter.org
- Auth: `X-API-Key` header (key from `ONET_API_KEY` env var)
- Purpose: map military occupation codes to civilian job titles
- Server-side proxy only, never call from frontend
- Endpoint: GET /api/v1/onet/search/?keyword={mos_code}

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
- Raw PDF bytes are never stored — extracted text only
- chat_history is persisted to DB server-side — the backend loads it on every call. Never pass history in the request body — it is ignored.
