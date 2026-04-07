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
  → returns {resume_id, military_text_preview}
```
Raw PDF bytes are never stored. Extracted text only.

### Phase 2 — Double-Duty Draft Call
```
Frontend → POST /api/v1/resumes/{id}/draft/ {job_description}
  → loads Resume by id + user (scoped)
  → calls compress_session_anchor(military_text, job_description)
      → single Claude API call
      → returns MilitaryTranslation (draft + clarifying_questions)
  → saves to Resume: job_description, session_anchor, civilian_title, summary, bullets
  → returns full MilitaryTranslation to frontend
Frontend splits response:
  → left pane: civilian_title + summary + bullets
  → right pane: clarifying_questions rendered as chat messages
```

### Phase 3 — Stateless Refinement Loop
```
Frontend → POST /api/v1/resumes/{id}/chat/
  {
    "message": "I want to emphasize the Trust & Safety angle",
    "history": [
      {"role": "assistant", "content": "...clarifying questions..."},
      {"role": "user", "content": "...previous answer..."}
    ]
  }
  → loads Resume.session_anchor from DB
  → builds messages: system_prompt + anchor + history + new message
  → calls Claude API
  → returns MilitaryTranslation (updated draft, clarifying_questions=[], assistant_reply="...")
  → saves updated civilian_title, summary, bullets to Resume
  → returns full MilitaryTranslation to frontend
Frontend:
  → left pane live-updates with new draft
  → right pane appends assistant_reply as chat message
```
**Key: raw military_text and job_description are never sent again after Phase 2.**
**Key: chat history is never persisted to DB — frontend owns it.**

### Phase 4 — Finalization
```
Frontend → PATCH /api/v1/resumes/{id}/finalize/
  {
    "civilian_title": "...",  # may include user's inline edits
    "summary": "...",
    "bullets": [...]
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
- Schema: MilitaryTranslation(civilian_title, summary, bullets, clarifying_questions, assistant_reply)
- Never call Claude API directly from views — always via services.py
- Response parsed from text block only, never tool_use block
- Markdown fences stripped before JSON parse

## Context Window Management
Every Claude API call stays under 5,000 tokens:

| Layer | Content | Tokens | Policy |
|---|---|---|---|
| System prompt | Role + output instructions | ~400 | Static, never changes |
| Session anchor | Compressed JD + resume identity | ~350 | Set once on draft call |
| Frontend history | Recent chat turns | ≤ 500 | Capped, passed from frontend |
| New user message | Current turn | ~100 | Current turn only |
| **Total** | | **~1,350** | |

compress_session_anchor() runs ONCE on the draft call. After that:
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
    bullets           = JSONField(default=list)
    approved_bullets  = JSONField(default=list)        # reserved for future granular approval
    rejected_bullets  = JSONField(default=list)        # reserved for future granular rejection
    is_finalized      = BooleanField(default=False)    # set True on finalize call
    created_at        = DateTimeField(auto_now_add=True)
    updated_at        = DateTimeField(auto_now=True)
```
Fields are blank=True on partial fields because upload creates the record before draft call.

## Frontend State Machine
```
IDLE        → upload dropzone visible, no resume_id in state
UPLOADED    → resume_id in state, JD textarea + "Generate Draft" button visible
DRAFTING    → loading spinner, both panes empty
REVIEWING   → split pane: draft left, chat right, "Approve & Finalize" button visible
FINALIZING  → inline bullet editing enabled, "Confirm Final" button
DONE        → redirect to /dashboard
```
Single `status` state variable drives all conditional renders.

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
- chat_history must NOT be persisted to DB — stateless by design
- multipart/form-data on upload endpoint only — JSON everywhere else

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