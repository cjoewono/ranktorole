# DATA_CONTRACT.md

---

## Phase 1 — PDF Upload

### POST /api/v1/resumes/upload/

Auth: JWT required
Content-Type: multipart/form-data

**Input**

```
file: <binary PDF>   # required, PDF only, max 10MB
```

**Output**

```json
{
  "id": "uuid",
  "created_at": "ISO8601"
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
  "job_description": "string" // required, 10–15000 chars
}
```

**Output**

```json
{
  "civilian_title": "string",
  "summary": "string",
  "roles": [
    {
      "title": "string",
      "org": "string",
      "dates": "string",
      "bullets": ["string"]
    }
  ],
  "clarifying_question": "string",
  "assistant_reply": ""
}
```

**Behavior**

- Loads Resume by {id} scoped to request.user (404 if not found or wrong user)
- Calls Claude API with military_text + job_description
- Saves: job_description, session_anchor, civilian_title, summary, roles to Resume
- clarifying_question: 1 targeted question based on gaps between resume and JD
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
  "message": "string" // required — user's reply to clarifying questions
}
```

**Output**

```json
{
  "civilian_title": "string",
  "summary": "string",
  "roles": [
    {
      "title": "string",
      "org": "string",
      "dates": "string",
      "bullets": ["string"]
    }
  ],
  "assistant_reply": "string"
}
```

**Behavior**

- Loads Resume.session_anchor and chat_history from DB (never raw military_text or job_description)
- Builds Claude payload: system_prompt + anchor + history + message
- Updates Resume: civilian_title, summary, roles with refined output
- assistant_reply: brief conversational confirmation from Claude
- history is loaded from DB on every call — backend is the source of truth. Any history key in the request body is ignored.

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
  "civilian_title": "string", // optional — user's inline edits
  "summary": "string", // optional — user's inline edits
  "roles": [
    // optional — user's inline edits
    {
      "title": "string",
      "org": "string",
      "dates": "string",
      "bullets": ["string"]
    }
  ]
}
```

**Output**

```json
{
  "id": "uuid",
  "civilian_title": "string",
  "summary": "string",
  "roles": [
    {
      "title": "string",
      "org": "string",
      "dates": "string",
      "bullets": ["string"]
    }
  ],
  "is_finalized": true,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**Validation Rules**

- civilian_title: optional string, max 200 chars
- summary: optional string, max 3,000 chars
- roles: optional list, max 20 items; each item: title (max 200), org (max 200), dates (max 100), bullets (max 10 items, each max 500 chars)

**Behavior**

- All fields optional — any provided field overwrites current Resume value
- Sets is_finalized = True
- Once finalized, POST /chat/ returns 409
- Finalization is not reversible via API (admin only)

**Error Responses**

- 400 → payload violates validation rules
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
    "roles": [
      {
        "title": "string",
        "org": "string",
        "dates": "string",
        "bullets": ["string"]
      }
    ],
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

/api/v1/contacts/ GET, POST, PATCH, DELETE
Auth: JWT required
All queries filtered by request.user — no cross-user access

---

## O\*NET Proxy (unchanged)

GET /api/v1/onet/search/?keyword={mos_code}
Auth: JWT required
Server-side proxy — proxies to O\*NET Web Services
Returns: {occupations: [{code, title}], skills: [string]}

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
- civilian_title, summary, roles: stored as validated LLM output, updated on every chat turn
- Raw Claude API response: never stored
- chat_history: stored in DB — backend loads and appends to it on every chat turn
- Raw PDF bytes: never stored — extracted text only
- Failed translation attempts: not stored

## Data Access Rules

- All Resume data scoped to authenticated user (filter by request.user)
- No PII in server logs (no military_text, no job_description, no bullets)
- No cross-user resume access
- No admin access to user resume content without explicit grant
- User can delete their own resumes at any finalization state

---

## User Profile

### GET /api/v1/auth/profile/

Auth: JWT required

**Output**

```json
{
  "id": "uuid",
  "email": "string",
  "username": "string",
  "profile_context": {},
  "tier": "free",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

`tier` is read-only. Values: `free` (default), `pro`.
