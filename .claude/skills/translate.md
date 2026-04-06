# Skill: Translation Service

Load this file when working on: Claude API integration,
translation endpoint, Pydantic schema, or resume output.

## Flow
POST /api/v1/translations/
  → translate_app/views.py (thin — validate input only)
  → backend/services/translation_service.py (all logic)
  → Claude API
  → Pydantic validation
  → save to Resume model
  → return structured JSON

## Claude API Integration
- SDK: anthropic (pip install anthropic)
- Model: claude-sonnet-4-20250514
- Env var: ANTHROPIC_API_KEY
- Max tokens: 1024
- Never call SDK from views — services.py only

## Input Schema
{
  "military_text": string,     # required, max 5000 chars
  "job_description": string    # required, max 5000 chars
}

## Output Schema (Pydantic)
class MilitaryTranslation(BaseModel):
    civilian_title: str        # real job market title
    summary: str               # 2-3 sentences, no jargon
    bullets: list[str]         # 3-5 items, action verb first

## Prompt Design
System: You are a professional resume writer specializing in
military-to-civilian career transitions.

User: Translate this military experience into civilian resume language.
Military background: {military_text}
Target job description: {job_description}
Return ONLY valid JSON matching this schema: {schema}

## Response Parsing
- Parse from text block only — never tool_use block
- Strip markdown fences (```json ... ```) before parsing
- Validate with Pydantic — raise ValueError on failure
- On failure: log error (no PII), return 422 to frontend

## NEVER
- Call Claude API from views
- Log military_text or job_description content
- Store raw API response — only store validated output
- Skip Pydantic validation
- Expose API key in any log or response

## ALWAYS
- Wrap API call in try/except
- Return structured error on failure (not raw exception)
- Save validated output to Resume model after success
- Scope resume save to request.user

## Testing
- Test valid input → valid MilitaryTranslation output
- Test malformed Claude response → 422 returned
- Test missing fields → 400 returned
- Mock Claude API in tests — do not make real API calls