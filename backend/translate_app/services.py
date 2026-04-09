from __future__ import annotations

import json
import logging
import os
import re

import anthropic
from pydantic import BaseModel, ValidationError

from .context import DecisionsLog, RollingChatWindow

logger = logging.getLogger(__name__)

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
    clarifying_question: str  # single high-impact question on draft call, "" on refinement turns
    assistant_reply: str      # "" on draft call, populated on chat turns


def compress_session_anchor(military_text: str, job_description: str) -> dict:
    """Run ONCE at session start. Returns compressed anchor dict stored to Resume.session_anchor."""
    schema = MilitaryTranslation.model_json_schema()
    user_message = (
        "Translate this military experience into civilian resume language.\n"
        f"Military background: {military_text}\n"
        f"Target job description: {job_description}\n"
        f"Return ONLY valid JSON matching this schema: {json.dumps(schema)}"
    )
    translation = call_claude([{"role": "user", "content": user_message}])
    return {
        "civilian_title": translation.civilian_title,
        "summary": translation.summary,
        "roles": [r.model_dump() for r in translation.roles],
    }


def build_messages(
    anchor: dict,
    decisions: DecisionsLog,
    chat_window: RollingChatWindow,
    new_user_message: str,
) -> list[dict]:
    """Assemble 4-layer context for every subsequent multi-turn call.

    Layer order:
      1. Anchor summary (compressed session context)
      2. Decisions log
      3. Prior chat turns (from RollingChatWindow)
      4. New user message with schema appended
    """
    # Layer 1
    roles_summary = ""
    for role in anchor.get("roles", []):
        if isinstance(role, dict):
            roles_summary += (
                f"\n  - {role.get('title', '')} at {role.get('org', '')} "
                f"({role.get('dates', '')})"
            )

    anchor_block = (
        "Session context (compressed):\n"
        f"Title: {anchor.get('civilian_title', '')}\n"
        f"Summary: {anchor.get('summary', '')}\n"
        f"Roles:{roles_summary}"
    )

    # Layer 2
    decisions_block = decisions.to_prompt_block()

    system_context = anchor_block
    if decisions_block:
        system_context += f"\n\n{decisions_block}"

    # Layer 3 — prior turns from chat window
    messages: list[dict] = list(chat_window.to_messages())

    # Layer 4 — new user message with system context prepended
    schema = MilitaryTranslation.model_json_schema()
    full_user_message = (
        f"{system_context}\n\n"
        f"{new_user_message}\n"
        f"Return ONLY valid JSON matching this schema: {json.dumps(schema)}"
    )
    messages.append({"role": "user", "content": full_user_message})

    return messages


def extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF. Returns concatenated page text."""
    import fitz  # noqa: PLC0415 — import inside function avoids load-time failure if not installed

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def _call_claude_typed(messages: list[dict], model_class):
    """Call Claude API and validate the text response against any Pydantic model class.

    Raises:
        anthropic.APIError: on network/API failure
        ValueError: if response cannot be parsed or validated
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=messages,
        )
    except anthropic.APIError:
        logger.error("Claude API error")
        raise

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


def call_claude_draft(military_text: str, job_description: str) -> MilitaryTranslation:
    """Single Claude call for the draft endpoint. Returns MilitaryTranslation with clarifying questions."""
    schema = MilitaryTranslation.model_json_schema()
    user_message = (
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


def call_claude_chat(anchor: dict, history: list[dict], message: str) -> MilitaryTranslation:
    """Stateless refinement call. Builds anchor-pair + history + new message context."""
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

    anchor_text = (
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
        # Anchor as first user turn so history (starting with assistant) alternates correctly
        messages = [{"role": "user", "content": anchor_text}]
        messages.extend(history)
        messages.append({"role": "user", "content": message + schema_instruction})

    return _call_claude_typed(messages, MilitaryTranslation)


def call_claude(messages: list[dict]) -> MilitaryTranslation:
    """Call Claude API and return Pydantic-validated MilitaryTranslation.

    Raises:
        anthropic.APIError: on network/API failure
        ValueError: if response cannot be parsed or validated
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=messages,
        )
    except anthropic.APIError:
        logger.error("Claude API error during translation call")
        raise

    # Parse from text block only — never tool_use block
    raw = ""
    for block in response.content:
        if block.type == "text":
            raw = block.text
            break

    # Strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
        return MilitaryTranslation(**data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error("Claude response parsing failed: %s", type(exc).__name__)
        raise ValueError("Invalid response from Claude API") from exc
