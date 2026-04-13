# Architecture — Military-to-Civilian Resume Translator

## Docker/Nginx Pattern

- All API calls use relative paths (/api/v1/...), never hardcoded hosts
- Nginx handles routing: /api/ → backend:8000, / → frontend:5173
- New env vars require docker compose down && up (restart insufficient)
- Migrations must re-run after full down/up cycle

## Django App Structure (from BridgeBoard)

- Each feature = its own Django app (e.g. translate_app, user_app)
- Namespace apps in urls.py to avoid endpoint collisions
- services.py handles all external API and LLM calls
- Views only handle request/response, nothing else

## Product Flow Architecture

### Phase 1 — PDF Ingestion

```
Frontend (dropzone) → multipart/form-data → POST /api/v1/resumes/upload/
  → PyMuPDF extracts text
  → Resume.objects.create(military_text=extracted, user=request.user)
  → returns {id, created_at}
```

Raw PDF bytes are never stored. Extracted text only.

### Phase 2 — Double-Duty Draft Call

```
Frontend → POST /api/v1/resumes/{id}/draft/ {job_description}
  → loads Resume by id + user (scoped)
  → calls call_claude_draft(military_text, job_description)
      → single Claude API call
      → returns MilitaryTranslation (draft + clarifying_question)
  → saves to Resume: job_description, session_anchor, civilian_title, summary, roles
  → returns full MilitaryTranslation to frontend
Frontend splits response:
  → left pane: civilian_title + summary + bullets
  → right pane: clarifying_questions rendered as chat messages
```

### Phase 3 — Stateful Refinement Loop

```
Frontend → POST /api/v1/resumes/{id}/chat/
  {
    "message": "I want to emphasize the Trust & Safety angle"
  }
  → loads Resume.session_anchor and chat_history from DB
  → builds messages: system_prompt + anchor + history + new message
  → calls Claude API
  → returns MilitaryTranslation (updated draft, assistant_reply="...")
  → saves updated civilian_title, summary, roles to Resume
  → appends new turn to chat_history
  → returns full MilitaryTranslation to frontend
Frontend:
  → left pane live-updates with new draft
  → right pane appends assistant_reply as chat message
```

**Key: raw military_text and job_description are never sent again after Phase 2.**
**Key: chat history is persisted to DB — backend loads it from DB on every call.**

### Phase 4 — Finalization

```
Frontend → PATCH /api/v1/resumes/{id}/finalize/
  {
    "civilian_title": "...",  # may include user's inline edits
    "summary": "...",
    "roles": [...]
  }
  → saves final state to Resume
  → sets Resume.is_finalized = True
  → returns finalized Resume
Frontend:
  → clears chat history state
  → redirects to /dashboard
```

## Claude API Integration Pattern

- Use anthropic Python SDK
- Pydantic model validates every response (fail-fast on bad JSON)
- Schema: MilitaryTranslation(civilian_title, summary, roles, clarifying_question, assistant_reply)
- Never call Claude API directly from views — always via services.py
- Response parsed from text block only, never tool_use block
- Markdown fences stripped before JSON parse

## Context Window Management

Every Claude API call stays under 5,000 tokens:

| Layer            | Content                         | Tokens     | Policy                               |
| ---------------- | ------------------------------- | ---------- | ------------------------------------ |
| System prompt    | Role + output instructions      | ~400       | Static, never changes                |
| Session anchor   | Compressed JD + resume identity | ~350       | Set once on draft call               |
| DB chat history  | Recent chat turns               | ≤ 500      | Loaded from DB, appended server-side |
| New user message | Current turn                    | ~100       | Current turn only                    |
| **Total**        |                                 | **~1,350** |                                      |

call_claude_draft() runs ONCE on the draft call. After that:

- Raw military_text (~1,400 tokens) → never sent again
- Raw job_description (~500 tokens) → never sent again
- session_anchor (~350 tokens) → loaded from DB on every subsequent call

## Resume Model

```python
class Resume(models.Model):
    id                = UUIDField(primary_key=True)
    user              = ForeignKey(User)
    military_text     = TextField()                    # extracted PDF text
    job_description   = TextField(blank=True)          # set on draft call
    session_anchor    = JSONField(null=True, blank=True) # set on draft call
    civilian_title    = CharField(max_length=255, blank=True)
    summary           = TextField(blank=True)
    roles             = JSONField(default=list)        # set on draft, updated on chat
    chat_history      = JSONField(default=list)        # populated by backend on every chat turn
    ai_initial_draft  = JSONField(null=True, blank=True) # set on draft, used for redline diff
    approved_bullets  = JSONField(default=list)        # reserved for future granular approval
    rejected_bullets  = JSONField(default=list)        # reserved for future granular rejection
    is_finalized      = BooleanField(default=False)    # set True on finalize call
    created_at        = DateTimeField(auto_now_add=True)
    updated_at        = DateTimeField(auto_now=True)
```

Fields are blank=True on partial fields because upload creates the record before draft call.

## Frontend Architecture

### AppShell Pattern

`App.jsx` renders an `AppShell` component that owns the persistent NavBar and mounts all
pages once. Pages are shown/hidden via CSS (`hidden` class) rather than unmounted — this
prevents NavBar remounts and eliminates layout flash when ResumeBuilder enters fullscreen.

```
App
└── AppShell
    ├── NavBar (always mounted)
    ├── <ForgeSetup />  (hidden when path ≠ /profile)
    ├── <CareerRecon />  (hidden when path ≠ /recon)
    ├── <Dashboard />  (hidden when path ≠ /dashboard)
    ├── <Contacts />   (hidden when path ≠ /contacts)
    └── <ResumeBuilder setFullscreen={...} />  (hidden when path ≠ /resume-builder)
```

`fullscreen` state lives in AppShell and is passed as `setFullscreen` to ResumeBuilder.
When the builder enters a split-pane phase, it calls `setFullscreen(true)` — AppShell
applies `overflow-hidden` to prevent body scroll during the split-pane layout.

### Career Recon

Standalone O*NET-powered career exploration tool at `/recon`. Zero LLM cost — pure
server-side proxy to O*NET's My Next Move for Veterans API. Three-phase UI:
SEARCH → RESULTS → DETAIL. Serves as a conversion funnel into the resume builder.

Backend: two views in onet_app — `OnetMilitarySearchView` (military search) and
`OnetCareerDetailView` (aggregated career report). Both use `OnetThrottle`.

### State Machine Hook

All resume builder logic lives in `frontend/src/hooks/useResumeMachine.js`:

- `initialState` — 9-field initial state
- `reducer` — 18 action cases
- `useEffect` — re-entry from Dashboard via `?id=&mode=` search params
- `handleGenerateDraft` — `useCallback`-wrapped, calls `generateDraft()` API
- `handleChatSend` — `useCallback`-wrapped, calls `sendChatMessage()`, dispatches optimistic + received actions

`ResumeBuilder.jsx` is JSX-only — it calls `useResumeMachine()` and passes results to children.

### State Machine Phases

```
IDLE        → upload dropzone visible, no resume_id in state
UPLOADED    → resume_id in state, JD textarea + "Generate Draft" button visible
LOADING     → re-entry from Dashboard: loading spinner while fetching resume from DB
DRAFTING    → loading spinner, both panes empty
REVIEWING   → split pane: draft left, chat right, "Approve & Finalize" button visible
FINALIZING  → inline bullet editing enabled, "Confirm Final" button
DONE        → export CTA + "Back to Dashboard" link
```

Single `phase` field in state drives all conditional renders.

### DraftPane Component Tree

```
DraftPane/ (index.jsx)
├── phase === REVIEWING  → read-only role cards + "Approve & Edit" button
├── phase === FINALIZING → <FinalizingEditor />
│   ├── Title + Summary inputs
│   ├── <BulletEditor /> per bullet
│   │   ├── Accordion header (current value)
│   │   ├── Textarea (edit)
│   │   ├── <DiffView /> (vs ai_initial_draft)
│   │   └── AI suggestion chip (Accept / Dismiss)
│   └── Sticky confirm button
└── phase === DONE       → Export PDF button + Back to Dashboard link
```

## PDF Extraction

- Library: PyMuPDF (pymupdf==1.24.11)
- Text-native PDFs extract cleanly — no OCR needed for Calvin's resume
- Two-column skills section extracts sequentially (left then right) — fine for LLM
- Extraction order: page 1 text + page 2 text, concatenated with newline
- Raw PDF bytes discarded after extraction

## Known Lessons

- docker compose restart does NOT load new env vars; must use down && up
- Use PersistentClient pattern for any local storage services
- Relative paths only — hardcoded IPs break in Docker networking
- chat_history IS persisted to DB — backend owns it; never pass it in request body
- multipart/form-data on upload endpoint only — JSON everywhere else
- AppShell pattern (CSS hide/show) prevents NavBar remounts and fullscreen flash
- Vite resolves directory imports to index.jsx — use this for component subfolders
- Custom hooks (useResumeMachine) keep page components as pure JSX; easier to test and reason about

## Tiered Throttling

Rate limits are tier-aware. Every throttled endpoint reads `request.user.tier` (free/pro) and looks up the rate from `settings.TIERED_THROTTLE_RATES[scope][tier]`.

| Scope           | Free   | Pro    | Endpoints                            |
| --------------- | ------ | ------ | ------------------------------------ |
| `user_upload`   | 3/day  | 15/day | POST /api/v1/resumes/upload/         |
| `user_draft`    | 1/day  | 5/day  | POST /api/v1/resumes/{id}/draft/     |
| `user_chat`     | 10/day | 50/day | POST /api/v1/resumes/{id}/chat/      |
| `user_finalize` | 3/day  | 15/day | PATCH /api/v1/resumes/{id}/finalize/ |
| `user_onet`     | 10/day | 30/day | GET /api/v1/onet/search/             |

All throttle classes live in `translate_app/throttles.py`. Cache key includes tier so upgrade/downgrade immediately takes effect. Falls back to `DEFAULT_THROTTLE_RATES` for unknown tiers.

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

## SSL / HTTPS (Production)

- Certbot runs on EC2 host: `sudo certbot certonly --webroot -w /var/lib/letsencrypt -d cjoewono.com -d www.cjoewono.com`
- Nginx serves ACME challenge on port 80, redirects all else to 443
- SSL certs mounted read-only into Nginx container via `/etc/letsencrypt` volume
- Django trusts `X-Forwarded-Proto: https` header from Nginx (`SECURE_PROXY_SSL_HEADER`)
- HSTS, CSP, X-Frame-Options, X-Content-Type-Options all set in Nginx
- Gunicorn on EC2: override backend command at launch — `docker compose run -d backend gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3`
- Dev workflow unchanged: Vite on host, backend in Docker with runserver, no Nginx
