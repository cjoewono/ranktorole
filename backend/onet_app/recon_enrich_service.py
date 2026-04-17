"""Claude Haiku 4.5 career enrichment for Career Recon."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date

import anthropic
import requests as http_requests
from django.conf import settings
from django.core.cache import cache
from pydantic import ValidationError

from translate_app.services import _get_client, strip_tags

from .schemas import CareerEnrichment

logger = logging.getLogger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"
MOS_TITLE_CACHE_TTL = 30 * 24 * 60 * 60  # 30 days — MOS titles don't change
ONET_V2_BASE = "https://api-v2.onetcenter.org"

_ENRICH_SYSTEM_PROMPT = (
    "You are a military-to-civilian career transition expert. You analyze "
    "how a veteran's specific background maps to a target civilian career. "
    "Return only valid JSON matching the requested schema. No preamble, no "
    "markdown fences, no commentary."
)


def _profile_fingerprint(profile_context: dict) -> str:
    skills = profile_context.get("skills", []) or []
    skills_str = ",".join(sorted(skills)) if isinstance(skills, list) else str(skills)
    parts = [
        profile_context.get("branch", ""),
        profile_context.get("mos", ""),
        profile_context.get("target_sector", ""),
        skills_str,
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _cache_key(onet_code: str, profile_context: dict) -> str:
    return f"recon_enrich:{onet_code}:{_profile_fingerprint(profile_context)}"


def _global_ceiling_key() -> str:
    return f"recon_enrich_global:{date.today().isoformat()}"


def _check_and_increment_global_ceiling() -> bool:
    key = _global_ceiling_key()
    ceiling = settings.RECON_ENRICH_DAILY_CEILING

    cache.add(key, 0, 86400)
    try:
        count = cache.incr(key)
    except (ValueError, NotImplementedError):
        count = cache.get(key, 0) + 1
        cache.set(key, count, 86400)

    if count > ceiling:
        logger.warning(
            "Recon enrichment daily ceiling hit: %d/%d — returning 503 until tomorrow",
            count, ceiling,
        )
        return False

    return True


def _resolve_mos_title(branch: str, mos: str) -> str:
    """Look up the canonical military title for a (branch, mos) pair from O*NET.

    Returns the title string on success, or empty string on miss.
    Cached 30 days per (branch, mos) key. Empty string is a deliberate sentinel
    — the prompt uses it as a 'known unknown' so Haiku won't invent a title.
    """
    if not branch or not mos:
        return ""

    cache_key = f"mos_title:{branch.lower()}:{mos.upper()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached  # May be empty string (cached miss)

    try:
        resp = http_requests.get(
            f"{ONET_V2_BASE}/veterans/military/",
            params={"keyword": mos, "branch": branch.lower()},
            headers={
                "Accept": "application/json",
                "X-API-Key": settings.ONET_API_KEY,
            },
            timeout=10,
        )
    except http_requests.RequestException:
        logger.warning("O*NET title lookup network error for %s/%s", branch, mos)
        return ""  # Don't cache transient network errors

    if not resp.ok:
        cache.set(cache_key, "", MOS_TITLE_CACHE_TTL)
        return ""

    try:
        data = resp.json()
    except ValueError:
        return ""

    target_code = mos.upper()
    for match in data.get("military_match", []):
        if match.get("code", "").upper() == target_code:
            title = match.get("title", "")
            cache.set(cache_key, title, MOS_TITLE_CACHE_TTL)
            return title

    cache.set(cache_key, "", MOS_TITLE_CACHE_TTL)
    return ""


def _build_enrichment_prompt(
    career_data: dict,
    profile_context: dict,
    mos_title: str = "",
) -> str:
    career_title = career_data.get("title", "Unknown")
    career_desc = career_data.get("description", "")
    career_skills = [s.get("name", "") for s in career_data.get("skills", [])][:10]
    career_knowledge = [k.get("name", "") for k in career_data.get("knowledge", [])][:10]
    salary = career_data.get("outlook", {}).get("salary", {})
    salary_median = salary.get("annual_median", "N/A")
    salary_low = salary.get("annual_10th", "N/A")
    salary_high = salary.get("annual_90th", "N/A")

    branch = profile_context.get("branch", "Military")
    mos = profile_context.get("mos", "")
    target_sector = profile_context.get("target_sector", "")
    user_skills = profile_context.get("skills", [])
    user_skills_str = ", ".join(user_skills) if user_skills else "Not specified"

    if mos_title:
        mos_line = f"- MOS/Rating/AFSC: {mos} — {mos_title}"
    else:
        mos_line = f"- MOS/Rating/AFSC: {mos} (specific duties not verified — do not invent)"

    schema = CareerEnrichment.model_json_schema()

    return (
        "Analyze how this veteran's background maps to the target civilian career.\n\n"
        "VETERAN PROFILE:\n"
        f"- Service Branch: {branch}\n"
        f"{mos_line}\n"
        f"- Target Sector: {target_sector}\n"
        f"- Self-Reported Skills: {user_skills_str}\n\n"
        "CIVILIAN CAREER:\n"
        f"- Title: {career_title}\n"
        f"- Description: {career_desc}\n"
        f"- Key Required Skills: {', '.join(career_skills)}\n"
        f"- Key Required Knowledge: {', '.join(career_knowledge)}\n"
        f"- Salary Range: ${salary_low} - ${salary_high} (Median: ${salary_median})\n\n"
        "CRITICAL RULES:\n"
        "- The MOS/Rating/AFSC title above is authoritative when provided. "
        "Use it verbatim. Do not invent or rename the military role.\n"
        "- If the MOS line says 'specific duties not verified', describe the "
        "veteran's background at branch level only (e.g., 'your Army service') "
        "and do not speculate about specific military duties.\n"
        "- Never invent a military job title, rating, or specialty description. "
        "If uncertain about the code's specific duties, speak to transferable "
        "branch-level skills rather than fabricating specifics.\n\n"
        "Guidance:\n"
        "- match_score: 90+ means MOS duties directly overlap with the role. "
        "60-80 means transferable leadership/soft skills apply but technical "
        "gaps exist. Below 50 means significant retraining needed. Be honest — "
        "do not inflate scores to be encouraging.\n"
        "- personalized_description: 2-3 sentences referencing THIS veteran's "
        "specific branch and authoritative MOS title (when provided). Not generic.\n"
        "- skill_gaps: 2-4 specific certifications, skills, or experiences the "
        "veteran likely needs to bridge (e.g., 'OSHA 30-Hour Card', "
        "'PMP certification', 'cloud infrastructure experience').\n"
        "- education_recommendation: 1-2 sentences on a realistic degree or "
        "certification path. Reference GI Bill options where appropriate.\n"
        "- transferable_skills: 4-6 skills from their military background that "
        "directly apply to this civilian role.\n\n"
        "DO NOT generate resume bullets, XYZ-format accomplishments, or "
        "fabricated metrics. The veteran will build their own bullets in the "
        "resume builder with their real numbers.\n\n"
        f"Return ONLY valid JSON matching this schema: {json.dumps(schema)}"
    )


def _call_haiku_typed(messages: list[dict], model_class):
    client = _get_client()

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1024,
            system=_ENRICH_SYSTEM_PROMPT,
            messages=messages,
            timeout=settings.RECON_ENRICH_TIMEOUT_SECONDS,
        )
    except anthropic.APIError as exc:
        logger.error("Haiku API error during enrichment: %s", str(exc))
        raise
    except Exception as exc:
        logger.error("Unexpected error calling Haiku: %s", str(exc))
        raise ValueError(f"Haiku API call failed: {str(exc)}") from exc

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
        logger.error("Haiku response parsing failed: %s", type(exc).__name__)
        raise ValueError("Invalid response from Haiku API") from exc


def enrich_career(career_data: dict, profile_context: dict) -> CareerEnrichment | None:
    onet_code = career_data.get("code", "")
    cache_key = _cache_key(onet_code, profile_context)

    cached = cache.get(cache_key)
    if cached is not None:
        try:
            logger.info("enrich_career cache_hit onet_code=%s", onet_code)
            return CareerEnrichment(**cached)
        except ValidationError:
            logger.warning("Corrupted enrichment cache entry for %s, refetching", cache_key)
            cache.delete(cache_key)

    if not _check_and_increment_global_ceiling():
        return None

    logger.info("enrich_career cache_miss onet_code=%s", onet_code)

    # Resolve canonical MOS title from O*NET — prevents Haiku hallucinating job titles
    mos_title = _resolve_mos_title(
        profile_context.get("branch", ""),
        profile_context.get("mos", ""),
    )

    try:
        prompt = _build_enrichment_prompt(career_data, profile_context, mos_title)
        result = _call_haiku_typed(
            [{"role": "user", "content": prompt}],
            CareerEnrichment,
        )

        result.personalized_description = strip_tags(result.personalized_description)
        result.education_recommendation = strip_tags(result.education_recommendation)
        result.skill_gaps = [strip_tags(s) for s in result.skill_gaps]
        result.transferable_skills = [strip_tags(s) for s in result.transferable_skills]

        cache.set(cache_key, result.model_dump(), settings.RECON_ENRICH_CACHE_TTL)

        return result
    except (ValueError, anthropic.APIError):
        return None
    except Exception:
        logger.exception("Unexpected enrichment failure")
        return None
