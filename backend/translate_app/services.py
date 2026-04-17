from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass

import anthropic
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


def strip_tags(text: str) -> str:
    """Remove any HTML/XML tags from text to prevent stored XSS in rendered output."""
    return re.sub(r'<[^>]+>', '', text)

_anthropic_client = None


def _get_client() -> anthropic.Anthropic:
    """Return the shared Anthropic client, creating it on first call (singleton)."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
    return _anthropic_client


_SYSTEM_PROMPT = (
    "You are a professional resume writer specializing in military-to-civilian career transitions. "
    "Your task is to translate military resume experience into compelling civilian language.\n\n"
    "SOURCE PRESERVATION RULES (non-negotiable):\n"
    "1. Every concrete fact in the input must be preserved in the output. "
    "This includes: dollar amounts, percentages, team sizes, portfolio values, "
    "client counts, durations, dates, quantities, and named scope ('$110M+', "
    "'12+ clients', '3-member team', 'award-recognized', 'program of record'). "
    "When you translate a bullet, carry its concrete facts forward.\n"
    "2. Never add concrete facts that do not appear in the input. "
    "If the input says 'managed equipment,' do not output 'managed $2M in equipment.' "
    "If a metric is not in the input, describe the outcome qualitatively — "
    "do not invent a number to fill the gap.\n"
    "3. Never inflate scope or seniority beyond what the input describes. "
    "'Assisted with' stays assistive. A squad leader does not become a "
    "'program manager.' Match the level of authority shown in the input.\n"
    "4. Preserve every role exactly as it appears (title, org, dates). "
    "Rewrite only the bullet points.\n"
    "5. Use strong past-tense civilian action verbs. Translate military "
    "jargon into civilian equivalents. But the underlying facts — including "
    "every number and scope indicator from the source — must remain.\n\n"
    "Your translation should read as if a civilian recruiter wrote it while "
    "still carrying every quantitative proof point the veteran earned.\n\n"
    "Return ONLY valid JSON — no markdown fences, no commentary."
)


class RoleEntry(BaseModel):
    title: str
    org: str
    dates: str
    bullets: list[str]


class MilitaryTranslation(BaseModel):
    civilian_title: str
    summary: str
    roles: list[RoleEntry]
    clarifying_question: str
    assistant_reply: str


@dataclass
class ChatResult:
    translation: MilitaryTranslation
    updated_history: list[dict]


def _build_profile_block(profile_context: dict | None) -> str:
    """Build the OPERATOR PROFILE prompt block from user profile_context."""
    if not profile_context:
        return ""
    parts = []
    if profile_context.get("branch"):
        parts.append(f"Military Branch: {profile_context['branch']}")
    if profile_context.get("mos"):
        parts.append(f"MOS/Rating: {profile_context['mos']}")
    if profile_context.get("target_sector"):
        parts.append(f"Target Civilian Sector: {profile_context['target_sector']}")
    if profile_context.get("skills"):
        skills = (
            ", ".join(profile_context["skills"])
            if isinstance(profile_context["skills"], list)
            else profile_context["skills"]
        )
        parts.append(f"Key Transferable Skills: {skills}")
    if not parts:
        return ""
    return "OPERATOR PROFILE:\n" + "\n".join(parts) + "\n\n"


def compress_session_anchor(military_text: str, job_description: str, profile_context: dict | None = None) -> dict:
    """
    Run ONCE at session start to produce the compact anchor stored in Resume.session_anchor.

    Calls Claude with the full military_text and job_description. The returned dict
    (civilian_title, summary, roles) is stored to the DB and reused on every subsequent
    chat call — the raw texts are never sent again after this call.

    Args:
        military_text: Extracted PDF text from the uploaded resume.
        job_description: The target civilian job description.
        profile_context: Optional user profile dict (branch, MOS, target_sector, skills).

    Returns:
        Dict with keys: civilian_title (str), summary (str), roles (list[dict]).

    Raises:
        ValueError: If Claude returns unparseable or invalid JSON.
    """
    schema = MilitaryTranslation.model_json_schema()

    profile_block = _build_profile_block(profile_context)

    user_message = (
        f"{profile_block}"
        "Translate this military experience into civilian resume language.\n"
        f"Military background: {military_text}\n"
        f"Target job description: {job_description}\n"
        f"Return ONLY valid JSON matching this schema: {json.dumps(schema)}"
    )
    translation = _call_claude_typed([{"role": "user", "content": user_message}], MilitaryTranslation)
    return {
        "civilian_title": translation.civilian_title,
        "summary": translation.summary,
        "roles": [r.model_dump() for r in translation.roles],
    }


def extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extract plain text from PDF bytes using PyMuPDF (fitz).

    Concatenates all pages with newline separators. Raw bytes are discarded
    after extraction — only the returned string is stored.

    Args:
        file_bytes: Raw PDF bytes (must not be empty; caller validates MIME type).

    Returns:
        Concatenated text from all pages. May be empty for image-only PDFs.

    Raises:
        Exception: Propagates any fitz/PyMuPDF errors for the caller to handle.
    """
    import fitz

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def _call_claude_typed(messages: list[dict], model_class):
    """
    Call Claude API and validate the text response against a Pydantic model class.

    Strips markdown fences before JSON parsing. After Pydantic validation, sanitises
    all string fields with strip_tags() to prevent stored XSS if output is ever
    rendered in an unescaped context (PDF export, email, etc.).

    Raises ValueError on JSON decode failure or Pydantic validation failure.
    Raises anthropic.APIError / Exception on network or API errors.
    """
    client = _get_client()

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=messages,
        )
    except anthropic.APIError as e:
        logger.error("Claude API error: %s", str(e))
        raise
    except Exception as e:
        logger.error("Unexpected error calling Claude: %s", str(e))
        raise ValueError(f"Claude API call failed: {str(e)}") from e

    raw = ""
    for block in response.content:
        if block.type == "text":
            raw = block.text
            break

    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
        result = model_class(**data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error("Claude response parsing failed: %s", type(exc).__name__)
        raise ValueError("Invalid response from Claude API") from exc

    # Sanitise all string fields to prevent stored XSS
    if hasattr(result, 'civilian_title'):
        result.civilian_title = strip_tags(result.civilian_title)
    if hasattr(result, 'summary'):
        result.summary = strip_tags(result.summary)
    if hasattr(result, 'clarifying_question'):
        result.clarifying_question = strip_tags(result.clarifying_question)
    if hasattr(result, 'assistant_reply'):
        result.assistant_reply = strip_tags(result.assistant_reply)
    if hasattr(result, 'roles'):
        for role in result.roles:
            role.title = strip_tags(role.title)
            role.org = strip_tags(role.org)
            role.dates = strip_tags(role.dates)
            role.bullets = [strip_tags(b) for b in role.bullets]

    return result


def call_claude_draft(
    military_text: str,
    job_description: str,
    profile_context: dict | None = None,
    job_title: str = "",
    company: str = "",
) -> MilitaryTranslation:
    """
    Generate the initial resume draft from military text and a job description.

    This is the first (and most expensive) Claude call in the session. It processes
    the full military_text and job_description, which are never sent to Claude again
    after this call.

    Args:
        military_text: Extracted PDF text from the uploaded resume.
        job_description: The target civilian job description (10–15000 chars).
        profile_context: Optional user profile dict (branch, MOS, target_sector, skills).

    Returns:
        MilitaryTranslation with civilian_title, summary, roles, clarifying_question,
        and assistant_reply (empty string on draft call).

    Raises:
        ValueError: If Claude returns unparseable or schema-invalid JSON.
        anthropic.APIError: On Claude API HTTP errors.
        Exception: On unexpected network or SDK errors.
    """
    schema = MilitaryTranslation.model_json_schema()

    profile_block = _build_profile_block(profile_context)

    job_context_block = ""
    if job_title or company:
        parts = []
        if job_title:
            parts.append(f"Target Job Title: {job_title}")
        if company:
            parts.append(f"Target Company/Agency: {company}")
        job_context_block = "\n".join(parts) + "\n\n"

    user_message = (
        f"{profile_block}"
        f"{job_context_block}"
        "Translate this military resume into a structured civilian resume draft.\n\n"
        "Instructions:\n"
        "- Extract EVERY role from the experience section of the PDF text.\n"
        "- For each role, preserve the title, org/location, and date range EXACTLY as written.\n"
        "- Rewrite ONLY the bullets for each role using strong civilian language "
        "(past-tense action verb first).\n"
        "- Do NOT add or remove roles — preserve the same number of roles as the original.\n"
        "- Do NOT cap the number of bullets per role — preserve the same count as the original.\n"
        "- Return a 2-3 sentence civilian-facing professional summary in the summary field.\n"
        "- Identify the SINGLE most important gap between the resume and the job description.\n"
        "- Return exactly ONE high-impact clarifying question in the clarifying_question field "
        "(a string, not a list) — make it specific to this JD, not generic.\n"
        "- If the resume already covers the JD well, ask about a quantifiable achievement "
        "or specific tool/methodology mentioned in the JD that is missing from the resume.\n"
        "- Set assistant_reply to an empty string \"\".\n\n"
        f"Military background:\n{military_text}\n\n"
        f"Target job description:\n{job_description}\n\n"
        f"Return ONLY valid JSON matching this schema: {json.dumps(schema)}"
    )
    return _call_claude_typed([{"role": "user", "content": user_message}], MilitaryTranslation)


def call_claude_chat(anchor: dict, history: list[dict], message: str) -> ChatResult:
    """
    Execute a stateful refinement turn using the session anchor and DB-loaded history.

    Builds the Claude message list from anchor + history + new message, calls Claude,
    and returns the updated translation along with the new history to persist.

    Args:
        anchor: The session_anchor dict stored at draft time (civilian_title, summary,
                roles, job_description_snippet, profile_context).
        history: Chat history loaded from the DB (list of {role, content} dicts).
                 This must come from the DB — never from the request body.
        message: The user's new chat message (max 2000 chars, validated by caller).

    Returns:
        ChatResult with the updated MilitaryTranslation and the new history to save.

    Raises:
        ValueError: If Claude returns unparseable or schema-invalid JSON.
        anthropic.APIError: On Claude API HTTP errors.
        Exception: On unexpected network or SDK errors.
    """
    schema = MilitaryTranslation.model_json_schema()

    roles_lines = []
    for role in anchor.get("roles", []):
        if isinstance(role, dict):
            roles_lines.append(
                f"  Role: {role.get('title', '')} | Org: {role.get('org', '')} "
                f"| Dates: {role.get('dates', '')}"
            )
            for b in role.get("bullets", []):
                roles_lines.append(f"    - {b}")

    roles_str = "\n".join(roles_lines) if roles_lines else "(no roles)"

    profile_block = _build_profile_block(anchor.get("profile_context"))

    anchor_text = (
        f"{profile_block}"
        "Current resume draft (session context):\n"
        f"Civilian title: {anchor.get('civilian_title', '')}\n"
        f"Summary: {anchor.get('summary', '')}\n"
        f"Roles:\n{roles_str}\n"
        f"Role context: {anchor.get('job_description_snippet', '')}"
    )

    schema_instruction = (
        "\n\nInstructions for this refinement turn:\n"
        "- Update the roles array based on user feedback.\n"
        "- Preserve role title, org, and dates EXACTLY — only rewrite bullets.\n"
        "- Do NOT add or remove roles.\n"
        "- Set clarifying_question to \"\".\n"
        "- Populate assistant_reply with a brief explanation of changes made.\n"
        f"\nReturn ONLY valid JSON matching this schema: {json.dumps(schema)}"
    )

    if not history:
        messages: list[dict] = [
            {"role": "user", "content": anchor_text + "\n\n" + message + schema_instruction}
        ]
    else:
        if history[0]["role"] == "user":
            combined = {
                "role": "user",
                "content": anchor_text + "\n\n" + history[0]["content"],
            }
            messages = [combined] + list(history[1:])
        else:
            messages = [{"role": "user", "content": anchor_text}]
            messages.extend(history)
        messages.append({"role": "user", "content": message + schema_instruction})

    translation = _call_claude_typed(messages, MilitaryTranslation)

    updated_history = list(history)
    updated_history.append({"role": "user", "content": message})
    updated_history.append({"role": "assistant", "content": translation.assistant_reply})

    return ChatResult(translation=translation, updated_history=updated_history)


