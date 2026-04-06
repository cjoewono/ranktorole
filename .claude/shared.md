# Shared Context — Military-to-Civilian Resume Translator

## Sources of Truth
| File | When to read |
|------|-------------|
| CLAUDE.md | Every session |
| TASKS.md | Before any work — do not skip |
| ARCHITECTURE.md | Before touching services, Docker, or Nginx |
| SECURITY.md | Before touching auth, .env, or user data |
| DATA_CONTRACT.md | Before touching translation service or Claude API |

## Session Start Checklist
Run silently before any work:
1. Read TASKS.md — confirm what is in progress and what is next
2. Verify docker compose services are accounted for (frontend, backend, db, nginx)
3. Check for pending migrations: `docker compose exec backend python manage.py migrate --check`
4. If any check fails, report before proceeding

## NEVER
- Hardcode API keys, secrets, or IP addresses
- Call Claude API directly from views — use translation_service.py only
- Edit migration files after they have been applied
- Run `docker compose down` — use `docker compose stop`
- Add pip or npm packages without explicit approval
- Modify docker-compose.yml or .env without instruction
- Create a new Django app without confirming the name
- Expose raw exception messages to the frontend
- Scope database queries without filtering by request.user
- Write to .env — only .env.example gets updated

## ALWAYS
- Read TASKS.md before starting any session
- Use relative API paths (/api/v1/...) — never hardcode hosts
- Filter all resume/translation queries by request.user
- Run `docker compose exec backend pytest` after any backend change
- Validate Claude API output with Pydantic before saving
- Reference SECURITY.md before touching auth or user data
- Use UUIDv4 for all model primary keys
- Keep views thin — all logic belongs in services.py
- After completing a task, update TASKS.md status

## Service Map
| Service | Internal | External |
|---------|----------|----------|
| frontend | :5173 | Nginx :80 |
| backend | :8000 | Nginx :80/api/ |
| db | :5432 | not exposed |
| nginx | — | :80 |

## Stack
React 18 + Vite + Tailwind | Django REST Framework | PostgreSQL | Docker Compose | Nginx | Claude API