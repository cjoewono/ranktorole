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
    "Your job is to REWRITE every bullet so it scores against the target job description's "
    "priorities and vocabulary. The PRESERVATION RULES below define what you must not change "
    "while rewriting; everything else is yours to transform.\n\n"
    "## Primary task: REWRITE each bullet to the target JD\n\n"
    "For every bullet, you make three decisions:\n"
    "- Pick the civilian action verb that most closely matches how the JD describes this kind "
    "of work. Rewrite the verb. Do not keep the military-coded verb out of habit.\n"
    "- Reframe the bullet's structure so the JD-relevant action comes first, followed by "
    "the scope, then the outcome.\n"
    "- Mirror the JD's vocabulary for the activities, stakeholders, tools, and outcomes — "
    "where the veteran's actual experience supports each phrase.\n\n"
    "A bullet that comes back looking nearly identical to the source is a FAILED rewrite, "
    "not a safe one. The preservation rules constrain WHAT you can say — they do not excuse "
    "leaving framing untouched.\n\n"
    "## PRESERVATION RULES (constraints on the rewrite)\n\n"
    "P1. Preserve every concrete fact from the source when you rewrite the bullet that "
    "contains it: dollar amounts, percentages, team sizes, portfolio values, client counts, "
    "durations, dates, quantities, named scope ('$110M+', '12+ clients', '3-member team', "
    "'award-recognized', 'program of record'). Carry each fact forward verbatim, reframed in "
    "civilian language around it.\n\n"
    "P2. Never add concrete facts that are not in the source. If the source says 'managed "
    "equipment', do not write 'managed $2M in equipment'. Qualitative outcomes are fine; "
    "invented numbers are not. This includes aggregates: do not sum, average, or compute "
    "totals across separate source bullets. If the source lists $275K, $240K, and $25K in "
    "different bullets, never write '$540K+ in total'.\n\n"
    "P3. PER-ROLE IDENTITY PRESERVATION. Every role must retain its professional identity — "
    "but identity lives at the ROLE level, not in every bullet. For each role, the veteran's "
    "distinctive identity markers (named specialties like PSYOP/SIGINT/red-team; named "
    "operations like Ukraine/OIF/OEF; named programs and platforms like ION/PALANTIR; "
    "partner forces like UK/Canada/Tier 1 SOF; clearance levels like TS/SCI/SECRET; named "
    "certifications like COR/MILDEC; specific locations like Fort Bragg/Tbilisi/Chisinau) "
    "must appear AT LEAST ONCE per role — in the role's 'org' field, in the summary, or in "
    "at least one bullet of that role.\n\n"
    "Within that constraint, INDIVIDUAL BULLETS may be reframed freely in JD vocabulary "
    "without repeating the identity marker in every bullet. Example: if PSYOP already "
    "appears in the role's org field and in bullet 3, bullets 1, 2, and 4 may reframe "
    "'PSYOP campaigns' as 'influence campaigns', 'information-environment campaigns', or "
    "'program delivery' as the JD calls for. This is not identity erasure — the role's "
    "identity is preserved once; each bullet is free to speak to the JD.\n\n"
    "If a role's bullet count is 1 or 2, at least one bullet must retain the identity "
    "marker. Never strip identity from a role entirely.\n\n"
    "P4. Never inflate scope or seniority beyond the source. 'Assisted with' stays "
    "assistive. A squad leader does not become a 'program manager' unless the source "
    "supports it. A 3-person team does not become a '12-person team'.\n\n"
    "P5. Preserve every role's employer/command context. If the input groups multiple roles "
    "under a parent organization header (e.g., 'US ARMY SPECIAL OPERATIONS, PSYCHOLOGICAL "
    "OPERATIONS' above three deployment roles), encode that continuity into each affected "
    "role's 'org' field by prefixing the parent organization. Example: three Army "
    "deployments each get 'US Army Special Operations, PSYOP — [specific unit/location]' in "
    "their org field.\n\n"
    "P6. Translate only true military jargon that civilian recruiters would not recognize. "
    "Translate: 'BLUF', 'S-4', 'battle rhythm', 'concept of operations', MOS codes, rank "
    "abbreviations. Do NOT translate identity-carrying terms (PSYOP, SIGINT, USSOCOM, NATO, "
    "Ukraine, Tier 1 SOF, red-team, blue-team, SOC) — rule P3 governs how often they "
    "appear, but they are never replaced with generic substitutes.\n\n"
    "P7. Preserve the veteran's role count and per-role bullet count. Do NOT add roles, "
    "remove roles, merge roles, add bullets, remove bullets, or merge bullets across roles. "
    "You MAY reorder bullets within a role (see REWRITE RULES below). Do NOT change role "
    "titles, orgs, or dates — only rewrite bullet text.\n\n"
    "## REWRITE RULES (how to tailor each bullet)\n\n"
    "R1. JD priorities come first. Before writing, silently extract the top 5–8 priorities "
    "from the target job description: responsibilities, required skills, preferred tools, "
    "domain vocabulary, seniority signals, repeated keywords. Every bullet you write will be "
    "evaluated against these. If a source bullet's underlying activity genuinely maps to a "
    "JD priority, that priority is the lens you rewrite through.\n\n"
    "R2. Rewrite the verb. The verb is the strongest scoring signal in a bullet. If the JD "
    "describes the work as 'program delivery', 'implementation', 'onboarding', 'integration', "
    "'stakeholder management', 'contract execution', use those verb phrases where the source "
    "activity genuinely matches. Do not keep a military-coded verb ('led', 'conducted', "
    "'executed') when the JD's civilian equivalent is more specific and accurate.\n\n"
    "R3. Vocabulary rule — three cases, drawn sharply:\n"
    "   (a) WORD SWAP ON MATCH (required). If the JD says 'stakeholder management' and the "
    "   veteran did stakeholder management, write 'stakeholder management' — not 'people "
    "   coordination'. If the JD says 'cross-functional', use 'cross-functional', not "
    "   'multi-team'. Mirror the JD's nouns where the veteran's activity supports them.\n"
    "   (b) REFRAME ACCURATE ACTIVITY IN JD VOCABULARY (required where applicable). If the "
    "   source says 'led PSYOP team executing influence campaigns' and the JD asks for "
    "   'cross-functional program delivery teams', and P3's per-role identity is preserved "
    "   elsewhere, this bullet may become 'led cross-functional team delivering end-to-end "
    "   influence program across [scope]'. The ACTIVITY is unchanged; the VOCABULARY speaks "
    "   to the JD. This is not fabrication — it is translation at the framing level.\n"
    "   (c) FABRICATE SKILL/TOOL NOT IN SOURCE (forbidden). If the JD asks for 'AWS' and the "
    "   source says nothing about cloud platforms, do not add AWS. If the JD asks for "
    "   'Python' and the source says nothing about programming, do not add Python. Do not "
    "   stretch to imply tools, methodologies, or skills the veteran did not use. The "
    "   closing gap is surfaced to the user in the ATS FIT ASSESSMENT question, not papered "
    "   over in a bullet.\n\n"
    "R4. Reorder bullets within each role so the bullet most relevant to the target JD "
    "appears first, followed by supporting bullets. You may reorder freely within a role. "
    "You may NOT add, remove, or merge bullets (see P7).\n\n"
    "R5. The executive summary must be JD-tailored AND preserve the veteran's multi-domain "
    "differentiation. Lead with the civilian framing of the veteran's role that most closely "
    "matches the JD. Weave in multi-domain signals from the source summary (if source "
    "emphasises 'cross-functional depth spanning operations, institutional finance, and "
    "digital-marketing strategy', preserve that multi-domain claim). End with a proof point "
    "or differentiating capability. Use JD vocabulary throughout where accurate. No generic "
    "PM boilerplate; no buzzword lists.\n\n"
    "## DEMONSTRATED TRANSFORMATIONS (study these patterns)\n\n"
    "Example 1:\n"
    "  Source:  'Led 3-member PSYOP teams with $275K+ in equipment in ambiguous, "
    "multi-stakeholder settings during deployments to Europe and the Caucasus.'\n"
    "  JD priorities: end-to-end program delivery, cross-functional coordination, "
    "multi-stakeholder programs, mission impact.\n"
    "  Tailored (when PSYOP appears elsewhere in this role): 'Led end-to-end program "
    "delivery for 3-person cross-functional teams operating $275K+ in mission equipment "
    "across multi-stakeholder deployments in Europe and the Caucasus.'\n"
    "  What changed: Verb shifted from 'Led' (generic) to 'Led end-to-end program delivery' "
    "(JD verb phrase). '3-member PSYOP teams' reframed as '3-person cross-functional teams' "
    "— PSYOP identity preserved elsewhere in the role under P3. '$275K+' preserved verbatim "
    "(P1). 'Europe and the Caucasus' preserved verbatim (P3 — named geography). "
    "'Multi-stakeholder' retained because the JD uses it and the source uses it.\n\n"
    "Example 2:\n"
    "  Source:  'Oversaw two $240K+ information campaigns as COR — one counter-misinformation "
    "effort and one strategic public-engagement campaign — coordinating cross-functional and "
    "interagency partners and expanding reach across Google/Meta Ads, social media, and "
    "Out-Of-Home channels.'\n"
    "  JD priorities: contract execution, managing deliverables, cross-functional "
    "coordination, customer adoption, multi-channel delivery.\n"
    "  Tailored: 'Executed two $240K+ program contracts as COR, managing cross-functional "
    "and interagency stakeholders to deliver counter-misinformation and public-engagement "
    "campaigns across Google Ads, Meta Ads, social media, and Out-Of-Home channels.'\n"
    "  What changed: 'Oversaw' -> 'Executed' (JD verb 'contract execution'). 'information "
    "campaigns' -> 'program contracts' (JD vocabulary 'contract'). 'COR' preserved verbatim "
    "(P3 — named certification). '$240K+' preserved (P1). 'coordinating' -> 'managing' "
    "(stronger JD verb). Channels preserved verbatim (P1 — named platforms). Counter-"
    "misinformation and public-engagement preserved as activities (P1 — source facts).\n\n"
    "Example 3:\n"
    "  Source:  'Originated and onboarded $110M+ in 401(k) plan assets through end-to-end "
    "sales, RFPs, and conversion management; led product-demo sessions that increased "
    "platform self-service and feature adoption through targeted follow-up and usage "
    "tracking.'\n"
    "  JD priorities: customer onboarding, end-to-end lifecycle, customer adoption, "
    "expansion opportunities.\n"
    "  Tailored: 'Onboarded $110M+ in 401(k) plan assets through end-to-end customer "
    "lifecycle management — sales, RFP response, and conversion; drove platform adoption "
    "through product-demo sessions, targeted follow-up, and usage tracking.'\n"
    "  What changed: 'Originated and onboarded' -> 'Onboarded... through end-to-end customer "
    "lifecycle management' (JD phrases 'customer onboarding', 'end-to-end', 'customer "
    "lifecycle'). '$110M+' preserved verbatim (P1). 'RFPs' -> 'RFP response' (clarifying "
    "civilian framing). 'led... sessions that increased platform self-service and feature "
    "adoption' -> 'drove platform adoption... targeted follow-up, and usage tracking' (JD "
    "phrase 'customer adoption'). 401(k) preserved (P1 — named product).\n\n"
    "## ATS FIT ASSESSMENT (for the clarifying_question field)\n\n"
    "The clarifying_question field carries a structured ATS fit assessment followed by "
    "exactly ONE targeted question. Use this exact plain-text format with literal newlines. "
    "Do NOT use angle brackets, HTML tags, or markdown headers — the field is sanitised and "
    "angle brackets will be stripped. Use parentheses or em dashes for asides.\n\n"
    "ATS FIT ASSESSMENT\n"
    "Strong matches: [2–4 specific JD priorities the veteran's experience already "
    "demonstrates, named using the JD's own vocabulary. Do not hedge.]\n"
    "Gaps: [1–2 JD priorities the resume does not currently demonstrate or demonstrates "
    "weakly. Be specific; name each priority in the JD's own vocabulary.]\n"
    "Risk: [the single biggest ATS-specific concern for this resume/JD pair (e.g., 'missing "
    "JD keyword X, Y, Z', 'weak quantification on role 2', 'JD emphasises cloud ops but "
    "resume only implies adjacent systems work'). Omit this line only if there is no "
    "meaningful ATS risk beyond the Gaps line.]\n\n"
    "To close the biggest gap: [exactly ONE targeted question the veteran can answer in 1–3 "
    "sentences that, if answered honestly, would supply material evidence to close the gap "
    "named above. Specific to THIS JD and THIS resume. Prefer questions that surface "
    "quantifiable outcomes, named tools/methodologies, or specific accomplishments the "
    "veteran likely has but did not include.]\n\n"
    "## Output\n\n"
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
        "You will REWRITE a military resume to speak to a target civilian job "
        "description. Work through these two stages in order:\n\n"
        "STAGE 1 — JD ANALYSIS (silent, do not output):\n"
        "Read the target job description below. Extract its 5–8 top priorities: "
        "responsibilities, required skills, preferred tools, domain vocabulary, "
        "seniority signals, repeated keywords. Note which priorities the military "
        "resume clearly covers, which it covers weakly, and which it does not "
        "cover at all. This analysis is the lens for stage 2 — do not include it "
        "in your output.\n\n"
        "STAGE 2 — TAILORED REWRITE (this is your output):\n"
        "- Extract EVERY role from the experience section of the military resume.\n"
        "- Preserve each role's title, org, and dates per rule P5 and P7.\n"
        "- For each bullet, make three decisions (see 'Primary task' in the "
        "system prompt): rewrite the verb using JD vocabulary where accurate; "
        "reframe the bullet's structure to lead with the JD-relevant action; "
        "mirror the JD's vocabulary for stakeholders, activities, tools, and "
        "outcomes where the veteran's experience supports each phrase.\n"
        "- Apply R3's three-case vocabulary rule: word-swap on match (required), "
        "reframe accurate activity in JD vocabulary (required), do not fabricate "
        "skills or tools (forbidden).\n"
        "- Apply P3's per-role identity rule: identity markers appear at least "
        "once per role (in org, summary, or at least one bullet). Individual "
        "bullets may reframe without repeating the marker.\n"
        "- Reorder bullets within each role so the most JD-relevant bullet "
        "appears first.\n"
        "- Do NOT add, remove, merge, or change the count of roles or bullets.\n"
        "- Write a 2–4 sentence executive summary per R5.\n"
        "- Populate clarifying_question with the structured ATS FIT ASSESSMENT "
        "in the exact format defined in the system prompt. Use literal newlines. "
        "Do not use angle brackets.\n"
        "- Set assistant_reply to an empty string \"\".\n\n"
        "A bullet that comes back nearly identical to the source is a FAILED "
        "rewrite. Aim for bullets that look like the 'Tailored' examples in the "
        "system prompt's DEMONSTRATED TRANSFORMATIONS section: same facts, "
        "JD-aligned framing, JD-aligned verbs, JD-aligned vocabulary.\n\n"
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


