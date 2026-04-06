# Architecture — Military-to-Civilian Resume Translator

## Docker/Nginx Pattern
- All API calls use relative paths (/api/v1/...), never hardcoded hosts
- Nginx handles routing: /api/ → backend:8000, / → frontend:5173
- New env vars require docker compose down && up (restart insufficient)
- Migrations must re-run after full down/up cycle

## Django App Structure (from BridgeBoard)
- Each feature = its own Django app (e.g. translate_app, job_app)
- Namespace apps in urls.py to avoid endpoint collisions
- services.py handles all external API and LLM calls
- Views only handle request/response, nothing else

## Claude API Integration Pattern
- Use anthropic Python SDK
- Pydantic model validates response (fail-fast)
- Schema: MilitaryTranslation(civilian_title, summary, bullets[])
- POST /api/v1/translate/ → translation_service.py → Claude API
- Never call Claude API directly from views
- Response must be parsed from text block, not tool_use block

## Job Description Input
- User pastes job description into frontend input field
- Frontend sends: {military_text, job_description} to POST /api/v1/translate/
- Claude API receives both fields and tailors translation to job description
- No external job API needed

## Known Lessons
- docker compose restart does NOT load new env vars; must use down && up
- Use PersistentClient pattern for any local storage services
- Relative paths only — hardcoded IPs break in Docker networking

## Dev vs Production

### Development
- Frontend: npm run dev on host (localhost:5173, HMR enabled)
- Backend: docker compose up (localhost:8000)
- Vite proxies /api/ to localhost:8000 via vite.config.js
- No Nginx needed in dev

### Production
- npm run build → dist/
- docker compose up --build
- Nginx serves dist/ and proxies /api/ → backend:8000