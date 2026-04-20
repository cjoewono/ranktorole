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
    "Your task is to translate military resume experience into compelling civilian language "
    "WHILE PRESERVING every distinctive professional identity marker the veteran earned, "
    "AND tailoring each bullet to maximise alignment with the target job description.\n\n"
    "SOURCE PRESERVATION RULES (non-negotiable):\n"
    "1. Every concrete fact in the input must be preserved in the output. "
    "This includes: dollar amounts, percentages, team sizes, portfolio values, "
    "client counts, durations, dates, quantities, and named scope ('$110M+', "
    "'12+ clients', '3-member team', 'award-recognized', 'program of record'). "
    "When you translate a bullet, carry its concrete facts forward.\n\n"
    "2. Never add concrete facts that do not appear in the input. "
    "If the input says 'managed equipment,' do not output 'managed $2M in equipment.' "
    "If a metric is not in the input, describe the outcome qualitatively — "
    "do not invent a number to fill the gap. "
    "This includes aggregates: do not sum, average, or compute totals across "
    "source numbers. If the input lists $275K, $240K, and $25K in separate "
    "bullets, do not write '$540K+ in total' anywhere — preserve each number "
    "only in its original context.\n\n"
    "3. PRESERVE ALL PROPER NOUNS VERBATIM. This includes: named operations "
    "('Ukraine', 'OIF', 'OEF'), named programs and platforms ('ION', 'PALANTIR'), "
    "named specialties ('PSYOP', 'SIGINT', 'red-team'), geographic locations "
    "('Tbilisi', 'Chisinau', 'Fort Bragg'), partner forces ('UK', 'Canada', "
    "'Tier 1 SOF'), clearance levels ('TS/SCI', 'SECRET'), named certifications "
    "('COR', 'MILDEC', 'Series 7'), and proper organizational names. "
    "These are searchable keywords in applicant tracking systems and recognizable "
    "credentials to recruiters. Generalizing 'Ukraine' to 'international' or "
    "'PSYOP' to 'cross-functional' destroys discoverability and career identity.\n\n"
    "4. Never inflate scope or seniority beyond what the input describes. "
    "'Assisted with' stays assistive. A squad leader does not become a "
    "'program manager.' Match the level of authority shown in the input.\n\n"
    "5. Preserve every role's employer/command context. If the input groups "
    "multiple roles under a parent organization (e.g., 'US ARMY SPECIAL "
    "OPERATIONS, PSYCHOLOGICAL OPERATIONS' as a header above three deployment "
    "roles), encode that continuity in each affected role's 'org' field by "
    "prefixing the parent organization. Example: if the source shows a Senior "
    "Program Manager role under a 'US Army Special Operations, PSYOP' header, "
    "the output 'org' should read 'US Army Special Operations, PSYOP — "
    "Information Warfare Center (IWC), Fort Bragg, NC' so the command-level "
    "narrative survives in flat role lists.\n\n"
    "6. Translate only true military jargon that civilian recruiters would not "
    "recognize. Translate: 'BLUF', 'S-4', 'battle rhythm', 'concept of "
    "operations', MOS codes, rank abbreviations. Do NOT translate: named "
    "specialties (PSYOP, SIGINT), operational named places (Ukraine, Iraq), "
    "security roles (red-team, blue-team, SOC), widely-recognized military "
    "organizations (USSOCOM, SOF, NATO), or anything a civilian defense/tech "
    "recruiter would already know.\n\n"
    "7. Summary fidelity: the executive summary must preserve the veteran's "
    "distinctive multi-domain signals from the source summary. If the source "
    "emphasizes 'cross-functional depth spanning operations, institutional "
    "finance, and digital-marketing strategy,' the output summary must "
    "preserve that multi-domain claim — do not reduce it to 'program "
    "management professional.' The summary is the veteran's differentiation; "
    "generic PM boilerplate erases it.\n\n"
    "8. Use strong past-tense civilian action verbs. Translate genuine "
    "military jargon into civilian equivalents (per rule 6). But the "
    "underlying facts — every number, proper noun, named operation, and "
    "scope indicator from the source — must remain intact.\n\n"
    "TAILORING RULES (apply ON TOP OF the preservation rules above):\n"
    "T1. Read the target job description FIRST. Silently extract the top "
    "5–8 priorities: required responsibilities, must-have skills, preferred "
    "tools and methodologies, domain vocabulary, seniority signals, and any "
    "repeated keywords. These are the recruiter's and ATS's scoring criteria. "
    "Every bullet you write will be evaluated against them.\n\n"
    "T2. Reframe each source bullet through the lens of those priorities. "
    "If the veteran's experience genuinely maps to a JD priority, FOREGROUND "
    "that mapping — lead with the JD-relevant action and outcome. A bullet "
    "about 'coordinating convoy movements across 3 FOBs' becomes, for a "
    "logistics PM role, 'Coordinated multi-site vehicle logistics across 3 "
    "forward operating bases, synchronizing delivery schedules and route "
    "risk assessments' — same facts, reframed to speak directly to "
    "'multi-site logistics,' 'scheduling,' and 'risk assessment' if those "
    "are JD priorities. The facts are unchanged; the framing is JD-aligned.\n\n"
    "T3. Mirror the JD's vocabulary where it is factually accurate. If the "
    "JD says 'stakeholder management' and the veteran managed stakeholders, "
    "use the phrase 'stakeholder management' — not 'people coordination.' "
    "If the JD says 'cross-functional collaboration' and the veteran did it, "
    "use that phrase. If the JD asks for a skill the veteran DOES NOT have, "
    "do not fabricate it and do not stretch to imply it — this is a bright "
    "line and the preservation rules above still bind absolutely.\n\n"
    "T4. Reorder bullets WITHIN each role to lead with the most JD-relevant "
    "accomplishment first, followed by supporting bullets. You may reorder "
    "freely within a role. You may NOT add roles, remove roles, change role "
    "titles/orgs/dates, or merge bullets across roles. You may NOT drop "
    "bullets — bullet count per role must match the source (this preserves "
    "the veteran's full record for honesty and for non-ATS human review).\n\n"
    "T5. The executive summary must be JD-tailored AND identity-preserving. "
    "It should (a) lead with the civilian framing of the veteran's role "
    "that most closely matches the JD, (b) weave in the veteran's "
    "multi-domain signals from rule 7, and (c) end with a proof point or "
    "differentiating capability. Use JD vocabulary where accurate. Do not "
    "write generic PM boilerplate; do not write a list of buzzwords.\n\n"
    "ATS ASSESSMENT (for the clarifying_question field — NEW behaviour):\n"
    "The clarifying_question field is no longer a single standalone "
    "question. It now carries a structured ATS fit assessment followed by "
    "exactly ONE targeted question. Write it in this exact plain-text "
    "format (use literal newlines; do NOT use angle brackets, HTML tags, "
    "or markdown headers):\n\n"
    "ATS FIT ASSESSMENT\n"
    "Strong matches: [one short line — 2–4 specific JD priorities that the "
    "veteran's experience already demonstrates. Name the priorities using "
    "the JD's own vocabulary. Do not hedge.]\n"
    "Gaps: [one short line — 1–2 JD priorities the resume does NOT "
    "currently demonstrate, or demonstrates weakly. Be specific; name the "
    "priority in the JD's own vocabulary.]\n"
    "Risk: [one short line — the single biggest ATS-specific concern for "
    "this resume/JD pair. Examples: 'missing JD keyword X,Y,Z', 'weak "
    "quantification on role 2', 'JD emphasises cloud ops but resume only "
    "implies adjacent systems work'. Omit this line only if there is no "
    "meaningful ATS risk beyond the Gaps line above.]\n\n"
    "To close the biggest gap: [exactly ONE targeted question the veteran "
    "can answer in 1–3 sentences that, if answered honestly, would supply "
    "material evidence to close the gap you named above. The question must "
    "be specific to THIS JD and THIS resume. Do not ask about rank or "
    "dates unless genuinely relevant. Prefer questions that surface "
    "quantifiable outcomes, named tools/methodologies, or specific "
    "accomplishments the veteran likely has but did not include.]\n\n"
    "Do NOT use angle brackets '<' or '>' anywhere in this field — they "
    "will be stripped by output sanitisation. Use parentheses or em dashes "
    "for asides instead.\n\n"
    "Your translation should read as if a civilian recruiter wrote it while "
    "carrying forward every quantitative proof point AND every identity-"
    "defining keyword the veteran earned, AND tailored every phrase to the "
    "target JD's priorities.\n\n"
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
        "You will tailor a military resume to a target civilian job "
        "description. Work through these two stages in order:\n\n"
        "STAGE 1 — JD ANALYSIS (silent, do not output):\n"
        "Read the target job description below and extract its 5–8 top "
        "priorities: responsibilities, required skills, preferred tools, "
        "domain vocabulary, seniority signals, and any repeated keywords. "
        "Note which of these the military resume clearly covers, which it "
        "covers weakly, and which it does not cover. Do not include this "
        "analysis in your output — it is the lens for stage 2.\n\n"
        "STAGE 2 — TAILORED TRANSLATION (this is your output):\n"
        "- Extract EVERY role from the experience section of the military "
        "resume.\n"
        "- For each role, preserve the title, org/location, and date range "
        "EXACTLY as written (see preservation rule 5 on parent-org "
        "prefixing in the system prompt).\n"
        "- Rewrite the bullets using strong past-tense civilian action "
        "verbs, applying the TAILORING RULES (T1–T5) from the system "
        "prompt. Each bullet should foreground whichever JD priority the "
        "underlying facts genuinely map to. Mirror the JD's vocabulary "
        "where factually accurate.\n"
        "- Reorder bullets WITHIN each role so the bullet most relevant "
        "to the JD appears first. Do NOT add, remove, or merge bullets — "
        "preserve the original per-role bullet count.\n"
        "- Do NOT add or remove roles.\n"
        "- Write a 2–4 sentence civilian-facing professional summary that "
        "is JD-tailored AND preserves the veteran's multi-domain "
        "differentiation (see rule 7 and T5).\n"
        "- Populate clarifying_question with a structured ATS FIT "
        "ASSESSMENT followed by ONE targeted question, in the exact "
        "format defined in the ATS ASSESSMENT section of the system "
        "prompt. Use literal newlines. Do not use angle brackets.\n"
        "- Set assistant_reply to an empty string \"\".\n\n"
        f"Target job description:\n{job_description}\n\n"
        f"Military background:\n{military_text}\n\n"
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


