RankToRole — Project Log

---

## April 6, 2026 | Sessions 01 + 02 | Phase 1 → Phase 3 Complete

### Session 01 — Phase 1: Project Setup & Claude Code Configuration
**Duration:** Morning session | **Status:** ✅ Complete

**Stack Confirmed**
- Frontend: React 18 + Vite + Tailwind CSS + React Router DOM
- Backend: Django REST Framework, Python 3.12
- Database: PostgreSQL 16 (named volume)
- AI: Claude API (claude-sonnet-4-20250514)
- Auth: JWT via SimpleJWT + Google OAuth 2.0
- Public API: O*NET Web Services (no key)
- Infrastructure: Docker Compose + Nginx
- Deployment: AWS EC2

**Architecture Decisions**
- Hybrid dev setup: Vite on host (HMR enabled), backend/db in Docker
- Vite proxies /api/ to localhost:8000 in dev
- Production: npm run build → dist/ → Nginx serves static + proxies API
- runserver in dev, gunicorn in production
- Named postgres volume (fixes BridgeBoard data loss on docker compose down)
- All API calls use relative paths — never hardcoded hosts

**Feature Decisions**
- User pastes job description manually — no job search API
- 2 CRUD models: Resume + Contact
- Google OAuth satisfies secret key requirement
- O*NET satisfies public API requirement
- UUIDs on all models
- Lazy loading on frontend components

**Security Decisions**
- JWT access token: 15 min expiry, stored in memory only
- JWT refresh token: 7 days, httpOnly cookie
- CORS whitelist frontend URL only
- DB port never exposed externally
- No PII in server logs
- IAM instance role on EC2 (no hardcoded AWS credentials)

**Issues Encountered & Resolved**

| Issue | Resolution |
|---|---|
| .gitignore corruption | Fixed manually, recommitted |
| zsh treating ! as history expansion | Run commands one at a time |
| zsh treating # as commands | Don't paste inline comments |
| Git not initialized | ran git init |
| GitHub repo not found on first push | Created repo on github.com/new |

---

### Session 02 — Phases 2 + 3: Context Window Management + Full Stack Build
**Duration:** Afternoon/evening session | **Status:** ✅ Complete

**Phase 2 — Context Window Management**

Four-layer context architecture keeps every Claude API call under 5,000 tokens:

| Layer | Content | Budget | Policy |
|---|---|---|---|
| 1 | System prompt | ~400 tokens | Static — never changes |
| 2 | Session anchor (compressed JD + resume) | ~700 tokens | Set once, always kept |
| 3 | Decisions log (approved/rejected bullets) | ~100/bullet | Never pruned |
| 4 | Rolling chat window | ≤ 2,000 tokens | Oldest pruned first |

Key classes: `DecisionsLog`, `RollingChatWindow`, `compress_session_anchor()`, `build_messages()`

**Phase 3 — Full Stack Build via Subagent Orchestration**

| Agent | Files Created | Time | Outcome |
|---|---|---|---|
| scaffold-agent | 45 | 2m 5s | Django project + Vite scaffold |
| models-agent | 12 | 3m 3s | All models, serializers, migrations |
| auth-agent | 8 | ~4m | JWT + Google OAuth, 6 endpoints |
| translate-agent | 7 | ~3m | context.py, services.py, 18 tests |
| auth-fix-agent | 2 | ~1m | Hybrid JWT — memory + httpOnly cookie |
| frontend-agent | 15 | 2m 42s | React Router, all pages, components |
| deploy-agent | 3 | 46s | docker-compose.yml, Dockerfile, nginx.conf |
| **Total** | **92** | **~17m** | **Full stack built** |

**Stack Verification**

| Check | Result |
|---|---|
| docker compose up --build | ✅ All 4 services started |
| 48 migrations applied | ✅ All OK |
| POST /api/v1/auth/register/ | ✅ UUID + JWT returned |
| POST /api/v1/auth/login/ | ✅ Tokens issued |
| Frontend loads at localhost | ✅ React app served by Nginx |
| API routing via Nginx | ✅ /api/ proxied to backend |

**Issues Encountered & Resolved**

| Issue | Resolution |
|---|---|
| Backend started before DB ready | Added healthcheck + depends_on: service_healthy |
| Nginx serving default page | root directive pointed to /html not /html/dist |
| WSL2 bind mount stale cache | docker compose down && up --build |
| registerRequest missing username | Agent fix — added username field to API call and form |
| localStorage JWT (security) | auth-fix-agent rewrote to hybrid pattern |
| Docker tests failing in agents | Expected — no containers at build time, syntax validated via ast.parse |

---

## April 6, 2026 | Session 03 | Feature Design — PDF Flow & Intelligent Refinement Loop

**Status:** ✅ Design complete — ready for implementation

### Context
Moved beyond the original single-shot translation model. Redesigned the core product flow to eliminate the LLM as a middleman and deliver a collaborative, cost-efficient resume tailoring experience.

**Trigger:** Reviewed Calvin's actual resume PDF (Google_Ops_Resume_Calvin_Joewono.pdf). Confirmed PDF is text-native (not scanned) — PyMuPDF will extract cleanly with no OCR needed. Two-column skills section will extract sequentially, which is fine for LLM consumption.

### Documentation Updated (end of Session 03)
The following files were revised to reflect the new PDF flow architecture:
- CLAUDE.md — updated LLM integration, URL map, Pydantic schema, cost reference
- ARCHITECTURE.md — rewrote product flow, Claude integration pattern, Resume model, frontend state machine
- DATA_CONTRACT.md — full rewrite: 4 endpoint contracts (upload, draft, chat, finalize)
- TASKS.md — old single-shot tasks marked complete, new 7-step sprint added, EC2 pushed to Phase 5

All docs now in sync with Session 03 design. Ready for implementation.

---

### New Product Flow

```
1. Upload PDF         → extract text, create Resume record, return resume_id
2. Paste JD           → single LLM call returns draft + 2-3 clarifying questions
3. Answer questions   → stateless refinement turns (history passed from frontend)
4. Approve & Finalize → user edits bullets inline, confirms, is_finalized = True
```

**Key design principle:** LLM never sees the raw PDF or JD again after call 1. All subsequent turns use the compressed session anchor (~350 tokens) + rolling frontend history. This keeps the refinement loop at ~1,250 input tokens per turn.

---

### Cost Analysis (claude-sonnet-4-20250514 — $3 input / $15 output per 1M tokens)

| Call | Input tokens | Output tokens | Cost |
|---|---|---|---|
| Call 1 — PDF + JD → draft + questions | ~2,300 | ~600 | ~$0.016 |
| Each refinement turn | ~1,250 | ~600 | ~$0.013 |
| Full session (call 1 + 3 turns) | — | — | **~$0.055** |
| With prompt caching enabled | — | — | **~$0.025–$0.035** |

At 1,000 sessions/month: **$25–$55/month**. Negligible at this scale.

---

### Architecture Decisions

**Pydantic schema expansion** — single JSON blob covers both UI panes on every call:
```python
class MilitaryTranslation(BaseModel):
    civilian_title: str
    summary: str
    bullets: list[str]
    clarifying_questions: list[str]  # 2-3 on draft call, [] on refinement turns
    assistant_reply: str             # "" on draft call, populated on chat turns
```

**Stateless refinement loop** — chat history passed from frontend on each request. Eliminates `chat_history` DB column. Justified by session length (3-4 turns max). Backend reconstructs context from `session_anchor` (DB) + `history` (request body) on every turn.

**Frontend state machine:**
```
IDLE → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE
```
Single `status` state variable drives all conditional renders. Split-pane layout: draft on left, chat on right.

---

### Schema Changes

**Resume model** — one migration, do it now before Phase 1 code:

| Field | Change |
|---|---|
| `job_description` | Add `blank=True` — upload creates record before JD exists |
| `civilian_title` | Add `blank=True` — same reason |
| `summary` | Add `blank=True` — same reason |
| `is_finalized` | **New** — `BooleanField(default=False)` |

**New dependency:** `pymupdf==1.24.11` → `requirements.txt` + Docker rebuild

---

### New URL Map

| Method | Endpoint | Phase | Purpose |
|---|---|---|---|
| POST | `/api/v1/resumes/upload/` | 1 | PDF → military_text, returns resume_id |
| POST | `/api/v1/resumes/{id}/draft/` | 2 | JD → draft + questions, sets session_anchor |
| POST | `/api/v1/resumes/{id}/chat/` | 3 | message+history → updated draft + reply |
| PATCH | `/api/v1/resumes/{id}/finalize/` | 4 | final edits → is_finalized=True |
| GET | `/api/v1/resumes/` | existing | dashboard list |
| GET | `/api/v1/resumes/{id}/` | existing | retrieve single |
| DELETE | `/api/v1/resumes/{id}/` | existing | delete |

---

### Implementation Order (next session)

1. Migration — `is_finalized`, `blank=True` on partial fields
2. `requirements.txt` — add `pymupdf==1.24.11`, Docker rebuild
3. `POST /api/v1/resumes/upload/` — PyMuPDF extraction, create Resume record
4. Update serializers — handle partial Resume state (fields empty until draft call)
5. `POST /api/v1/resumes/{id}/draft/` — JD input, double-duty LLM call, save anchor
6. `POST /api/v1/resumes/{id}/chat/` — stateless refinement, update draft fields
7. `PATCH /api/v1/resumes/{id}/finalize/` — save final state, flip is_finalized
8. Frontend — replace Translator page with split-pane + status machine + file dropzone
9. Smoke test full flow end-to-end

**Start next session with:**
> "Let's continue RankToRole — implement the PDF flow. Start with the migration and requirements, then the upload endpoint."

---

Project log maintained: github.com/cjoewono/ranktorole
Last updated: April 6, 2026 — Session 03 design complete, implementation ready

## April 7, 2026 | Session 04 | Phase 4 Complete — PDF Builder Flow

**Status:** ✅ Complete

### Step 0 — Code Review & Bug Fixes
Six pre-existing bugs identified and fixed before any new code:

| Fix | File | Issue |
|---|---|---|
| 1 | contacts.js | PUT → PATCH on updateContact |
| 2 | views.py | ResumeDetailView missing delete() method |
| 3 | Contacts.jsx | phone field not in Contact model — removed from frontend |
| 4 | TASKS.md | All Phase 3 tasks marked [x] |
| 5 | models.py | is_finalized BooleanField added + migration 0002 applied |
| 6 | requirements.txt | pymupdf==1.24.11 added |

pytest: 38/43 passing (5 pre-existing rate-limiter failures)

### Rate Limiter Fix
LoginRateThrottle set directly on view class — global settings override
had no effect. Fixed via monkeypatch.setattr + cache.clear() in autouse
fixture. Result: 43/43 passing. Committed.

### Phase 4A — Backend (4 new endpoints)
Built by backend agent, all endpoints verified via pytest:

| Endpoint | View | Notes |
|---|---|---|
| POST /api/v1/resumes/upload/ | ResumeUploadView | PyMuPDF extraction, MIME validation |
| POST /api/v1/resumes/{id}/draft/ | ResumeDraftView | DraftResponse Pydantic schema, session anchor compression |
| POST /api/v1/resumes/{id}/chat/ | ResumeChatView | Stateless — history passed from frontend, 409 if finalized |
| PATCH /api/v1/resumes/{id}/finalize/ | ResumeFinalizeView | Sets is_finalized=True, 409 if already finalized |

pytest: 38/43 → baseline held (pre-existing failures only)

### Phase 4B — Frontend (6 new files, 2 modified)
Built via 7-task subagent execution with spec review + code review per task.

**Files created:**
- frontend/src/api/resumes.js
- frontend/src/pages/ResumeBuilder.jsx
- frontend/src/components/SplitPane.jsx
- frontend/src/components/DraftPane.jsx
- frontend/src/components/ChatPane.jsx
- frontend/src/components/UploadForm.jsx

**Files modified:**
- frontend/src/App.jsx — /resume-builder route added
- frontend/src/pages/Dashboard.jsx — "Open Builder" button + is_finalized badge

**Key fixes caught during code review:**
- CHAT_FAILED action added (orphaned optimistic message on failure)
- DRAFT_FAILED action added (user stuck in DRAFTING with no retry path)
- Dead err.message.includes("409") string check removed
- FinalizingEditor uses fresh-mount pattern (not useEffect sync)
- MIME check uses file.type not extension
- FormData Content-Type fix in client.js (instanceof FormData → delete header)

**State machine (useReducer):**
IDLE → UPLOADED → DRAFTING → REVIEWING → FINALIZING → DONE

### Smoke Test Results

| Step | Result | Notes |
|---|---|---|
| 1. Dashboard shows both buttons | ✅ | Stale Docker volume required purge |
| 2. /resume-builder loads | ✅ | ResumeBuilder-BPmMJy3m.js chunk confirmed |
| 3. PDF upload → 201 | ✅ | Content-Type fix resolved multipart issue |
| 4. Generate Draft → split pane | ✅ | Blocked by zero API credits — resolved |
| 5. Clarifying questions as chat bubbles | ✅ | 3 targeted questions rendered |
| 6. Chat reply → draft updates | ✅ | Stateless refinement working |
| 7/8. Finalize flow | ✅ | Editable fields → DONE state |
| 9. Dashboard Finalized badge | ✅ | Green pill renders correctly |

**Issues encountered:**

| Issue | Resolution |
|---|---|
| Stale frontend_dist volume | docker volume rm + rebuild |
| Content-Type: undefined not removing header | instanceof FormData → delete headers["Content-Type"] in client.js |
| Zero API credits | Added credits + rotated to funded workspace key |
| ANTHROPIC_API_KEY not reloading | docker compose up -d to pick up new .env |

### Output Quality
Draft call for military background → "Technical Program Manager - Analytics & Data Solutions"
with quantified bullets and targeted clarifying questions about BI tooling, SQL,
and marketing analytics. Translation quality confirmed strong end-to-end.

### Known Issues (non-blocking)
- DraftPane rendering more bullets than 3-5 specified in DATA_CONTRACT — prompt
  engineering issue in call_claude_draft, not a UI bug. Follow-up fix needed.

### Next Session
UI/UX improvements before EC2 deployment.
EC2 deployment pushed to Phase 5 (after UI/UX work complete).

---
Project log maintained: github.com/cjoewono/ranktorole
Last updated: April 7, 2026 — Phase 4 complete, smoke tested

