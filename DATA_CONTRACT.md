# DATA_CONTRACT.md

## Translation Endpoint
POST /api/v1/translations/
Auth: JWT required

### Input
{
  "military_text": string,      # required, 10–5000 chars
  "job_description": string     # required, 10–5000 chars
}

### Output
{
  "id": uuid,
  "civilian_title": string,     # real job market title
  "summary": string,            # 2-3 sentences, zero military jargon
  "bullets": string[],          # 3-5 items, past-tense action verb first
  "created_at": ISO8601
}

### Validation Rules
- bullets: minimum 3, maximum 5 items
- bullets: each must begin with a past-tense action verb
- summary: no military acronyms (MOS, SFC, SSG, etc.)
- civilian_title: must be a recognized civilian job title
- All fields required — no partial responses stored

### Error Responses
400 → missing or invalid input fields
401 → missing or expired JWT
422 → Claude API returned unparseable response
500 → unexpected server error (generic message only)

## Resume Model Storage
Stored after successful Pydantic validation only:
- military_text: stored (user owns their data)
- job_description: stored (user owns their data)
- civilian_title, summary, bullets: stored as validated output
- Raw Claude API response: never stored

## Contact Endpoint
/api/v1/contacts/   GET, POST, PUT, DELETE
Auth: JWT required
All queries filtered by request.user — no cross-user access

## O*NET Proxy
GET /api/v1/onet/search/?code={mos_code}
Auth: JWT required
Server-side proxy only — key never exposed to frontend
Returns: {title, description, related_civilian_titles[]}

## Auth Endpoints (no JWT required)
POST /api/v1/auth/register/
POST /api/v1/auth/login/
POST /api/v1/auth/refresh/
GET  /api/v1/auth/google/
POST /api/v1/auth/google/callback/

## User Data Rules
- Resume data scoped to authenticated user only
- No PII in server logs (no military_text, no job_description)
- Failed translation attempts not stored
- User can delete their own resumes (DELETE /api/v1/resumes/{id}/)
- No admin access to user resume content without explicit grant