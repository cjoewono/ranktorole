# DATA_CONTRACT.md

---

## Phase 1 — PDF Upload

### POST /api/v1/resumes/upload/
Auth: JWT required
Content-Type: multipart/form-data

**Input**
```
resume_file: <binary PDF>   # required, PDF only, max 10MB
```

**Output**
```json
{
  "id": "uuid",
  "military_text_preview": "string"   // first 300 chars of extracted text
}
```

**Validation Rules**
- File must be PDF (validate MIME type server-side)
- Max file size: 10MB (enforced by Nginx client_max_body_size)
- Extraction must return non-empty string

**Error Responses**
- 400 → missing file, wrong file type, or empty extraction result
- 401 → missing or expired JWT
- 500 → unexpected extraction failure

---

## Phase 2 — Draft Generation

### POST /api/v1/resumes/{id}/draft/
Auth: JWT required
Content-Type: application/json

**Input**
```json
{
  "job_description": "string"   // required, 10–5000 chars
}
```

**Output**
```json
{
  "id": "uuid",
  "civilian_title": "string",
  "summary": "string",
  "bullets": ["string"],
  "clarifying_questions": ["string"],
  "assistant_reply": "",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**Behavior**
- Loads Resume by {id} scoped to request.user (404 if not found or wrong user)
- Calls Claude API with military_text + job_description
- Saves: job_description, session_anchor, civilian_title, summary, bullets to Resume
- clarifying_questions: 2-3 targeted questions based on gaps between resume and JD
- assistant_reply: always empty string on draft call

**Validation Rules**
- bullets: 3-5 items, each begins with past-tense action verb
- clarifying_questions: 2-3 items, grounded in the actual draft
- summary: no military acronyms (MOS, SFC, SSG, etc.)
- civilian_title: recognized civilian job title

**Error Responses**
- 400 → missing or invalid job_description
- 401 → missing or expired JWT
- 404 → resume not found or not owned by user
- 422 → Claude API returned unparseable or invalid response
- 503 → Claude API unavailable

---

## Phase 3 — Refinement Chat

### POST /api/v1/resumes/{id}/chat/
Auth: JWT required
Content-Type: application/json

**Input**
```json
{
  "message": "string",       // required — user's reply to clarifying questions
  "history": [               // required — full chat history from frontend state
    {"role": "assistant", "content": "string"},
    {"role": "user", "content": "string"}
  ]
}
```

**Output**
```json
{
  "id": "uuid",
  "civilian_title": "string",
  "summary": "string",
  "bullets": ["string"],
  "clarifying_questions": [],
  "assistant_reply": "string",
  "updated_at": "ISO8601"
}
```

**Behavior**
- Loads Resume.session_anchor from DB (never raw military_text or job_description)
- Builds Claude payload: system_prompt + anchor + history + message
- Updates Resume: civilian_title, summary, bullets with refined output
- clarifying_questions: always [] on chat turns
- assistant_reply: brief conversational confirmation from Claude
- history is never saved to DB — stateless by design

**Error Responses**
- 400 → missing message or malformed history
- 401 → missing or expired JWT
- 404 → resume not found or not owned by user
- 409 → resume is already finalized (is_finalized=True)
- 422 → Claude API returned unparseable response
- 503 → Claude API unavailable

---

## Phase 4 — Finalization

### PATCH /api/v1/resumes/{id}/finalize/
Auth: JWT required
Content-Type: application/json

**Input**
```json
{
  "civilian_title": "string",   // optional — user's inline edits
  "summary": "string",          // optional — user's inline edits
  "bullets": ["string"]         // optional — user's inline edits
}
```

**Output**
```json
{
  "id": "uuid",
  "civilian_title": "string",
  "summary": "string",
  "bullets": ["string"],
  "is_finalized": true,
  "updated_at": "ISO8601"
}
```

**Behavior**
- All fields optional — any provided field overwrites current Resume value
- Sets is_finalized = True
- Once finalized, POST /chat/ returns 409
- Finalization is not reversible via API (admin only)

**Error Responses**
- 401 → missing or expired JWT
- 404 → resume not found or not owned by user
- 409 → already finalized

---

## Existing Endpoints (unchanged)

### GET /api/v1/resumes/
Auth: JWT required
Returns list of all resumes for authenticated user, ordered by -created_at.

**Output**
```json
[
  {
    "id": "uuid",
    "civilian_title": "string",
    "summary": "string",
    "bullets": ["string"],
    "is_finalized": true,
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  }
]
```

### GET /api/v1/resumes/{id}/
Auth: JWT required
Returns single resume scoped to request.user.

### DELETE /api/v1/resumes/{id}/
Auth: JWT required
Deletes resume. Works on finalized and unfinalized resumes.

---

## Contact Endpoint (unchanged)
/api/v1/contacts/   GET, POST, PATCH, DELETE
Auth: JWT required
All queries filtered by request.user — no cross-user access

---

## O*NET Proxy (unchanged)
GET /api/v1/onet/search/?code={mos_code}
Auth: JWT required
Server-side proxy only — never call from frontend
Returns: {title, description, related_civilian_titles[]}

---

## Auth Endpoints (no JWT required)
```
POST /api/v1/auth/register/
POST /api/v1/auth/login/
POST /api/v1/auth/refresh/
POST /api/v1/auth/logout/
GET  /api/v1/auth/google/
POST /api/v1/auth/google/callback/
```

---

## Resume Model Storage Rules
- military_text: stored (extracted from PDF — user owns their data)
- job_description: stored (user owns their data)
- session_anchor: stored (compressed context — never raw text)
- civilian_title, summary, bullets: stored as validated LLM output, updated on every chat turn
- Raw Claude API response: never stored
- chat_history: never stored — frontend owns it, passed on every chat request
- Raw PDF bytes: never stored — extracted text only
- Failed translation attempts: not stored

## Data Access Rules
- All Resume data scoped to authenticated user (filter by request.user)
- No PII in server logs (no military_text, no job_description, no bullets)
- No cross-user resume access
- No admin access to user resume content without explicit grant
- User can delete their own resumes at any finalization state