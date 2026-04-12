from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass

import anthropic
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

_anthropic_client = None


def _get_client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
    return _anthropic_client


_SYSTEM_PROMPT = (
    "You are a professional resume writer specializing in "
    "military-to-civilian career transitions. "
    "Your task is to translate military resume experience into compelling civilian language. "
    "Preserve every role exactly as it appears (title, org, dates). "
    "Rewrite only the bullet points using strong civilian language with a past-tense action verb first. "
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
    """Run ONCE at session start. Returns compressed anchor dict stored to Resume.session_anchor."""
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
    """Extract text from PDF bytes using PyMuPDF. Returns concatenated page text."""
    import fitz

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def _call_claude_typed(messages: list[dict], model_class):
    """Call Claude API and validate the text response against any Pydantic model class."""
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
        return model_class(**data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error("Claude response parsing failed: %s", type(exc).__name__)
        raise ValueError("Invalid response from Claude API") from exc


def call_claude_draft(
    military_text: str,
    job_description: str,
    profile_context: dict | None = None,
) -> MilitaryTranslation:
    """Single Claude call for the draft endpoint."""
    schema = MilitaryTranslation.model_json_schema()

    profile_block = _build_profile_block(profile_context)

    user_message = (
        f"{profile_block}"
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
    """Stateful refinement call. Builds anchor + history + new message context."""
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


