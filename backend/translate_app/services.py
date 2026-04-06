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
    "military-to-civilian career transitions."
)


class MilitaryTranslation(BaseModel):
    civilian_title: str
    summary: str
    bullets: list[str]


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
        "bullets": translation.bullets,
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
    anchor_block = (
        "Session context (compressed):\n"
        f"Title: {anchor.get('civilian_title', '')}\n"
        f"Summary: {anchor.get('summary', '')}\n"
        f"Initial bullets: {'; '.join(anchor.get('bullets', []))}"
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
            max_tokens=1024,
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
