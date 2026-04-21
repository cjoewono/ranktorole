"""
Shared Haiku helpers for Recon.

After the Recon rebuild (April 2026), this module exports infrastructure used
by recon_app:

- _resolve_mos_title()                — canonical MOS title via O*NET veterans lookup
- _check_and_increment_global_ceiling — atomic daily spend ceiling across workers
- _call_haiku_typed()                 — Anthropic call with Pydantic validation

The legacy enrich_career()/BrainstormEnrichment flow has been removed.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date

import anthropic
import requests as http_requests
from django.conf import settings
from django.core.cache import cache
from pydantic import ValidationError

from translate_app.services import _get_client

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


# Navy officer designators are not indexed in O*NET's veterans database.
# Source: https://en.wikipedia.org/wiki/List_of_United_States_Navy_officer_designators
# https://www.mynavyhr.navy.mil/Career-Management/Community-Management/
# Covers URL (Unrestricted Line), RL (Restricted Line), Staff Corps, Limited
# Duty, and Chief Warrant Officer communities. Format matches O*NET return
# shape: "Title (Navy - Officer)" — keeps downstream prompt consistent.
NAVY_OFFICER_DESIGNATORS = {
    # Unrestricted Line (URL) Officers — operational command track
    "1110": "Surface Warfare Officer (Navy - Officer)",
    "1120": "Submarine Officer (Navy - Officer)",
    "1130": "Special Warfare Officer / SEAL (Navy - Officer)",
    "1140": "Special Operations Officer / EOD (Navy - Officer)",
    "1310": "Pilot (Navy - Officer)",
    "1320": "Naval Flight Officer (Navy - Officer)",
    "1390": "Aviation Maintenance Duty Officer (Navy - Officer)",

    # Restricted Line (RL) Officers — specialty/technical track
    "1440": "Engineering Duty Officer (Navy - Officer)",
    "1460": "Aerospace Engineering Duty Officer (Navy - Officer)",
    "1510": "Aerospace Engineering Duty Officer - Engineering (Navy - Officer)",
    "1610": "Special Duty Officer - Intelligence (Navy - Officer)",
    "1710": "Special Duty Officer - Public Affairs (Navy - Officer)",
    "1720": "Special Duty Officer - Foreign Area Officer (Navy - Officer)",
    "1810": "Information Warfare Officer (Navy - Officer)",
    "1820": "Cryptologic Warfare Officer (Navy - Officer)",
    "1830": "Intelligence Officer (Navy - Officer)",
    "1840": "Cyber Warfare Engineer (Navy - Officer)",

    # Staff Corps Officers — professional/support
    "2100": "Medical Corps Officer (Navy - Officer)",
    "2200": "Dental Corps Officer (Navy - Officer)",
    "2300": "Medical Service Corps Officer (Navy - Officer)",
    "2900": "Nurse Corps Officer (Navy - Officer)",
    "2500": "Judge Advocate General's Corps Officer (Navy - Officer)",
    "3100": "Supply Corps Officer (Navy - Officer)",
    "4100": "Chaplain Corps Officer (Navy - Officer)",
    "5100": "Civil Engineer Corps Officer (Navy - Officer)",

    # Limited Duty Officers (LDO) — common specialties
    "6110": "Limited Duty Officer - Deck (Navy - Officer)",
    "6120": "Limited Duty Officer - Operations (Navy - Officer)",
    "6130": "Limited Duty Officer - Engineering/Repair (Navy - Officer)",
    "6160": "Limited Duty Officer - Aviation Operations (Navy - Officer)",
    "6180": "Limited Duty Officer - Supply (Navy - Officer)",

    # Chief Warrant Officers (CWO) — common specialties
    "7110": "Chief Warrant Officer - Boatswain (Navy - Officer)",
    "7130": "Chief Warrant Officer - Engineering Technician (Navy - Officer)",
    "7180": "Chief Warrant Officer - Supply Corps (Navy - Officer)",
}

# Coast Guard ratings are not indexed in O*NET's veterans database.
# Source: Official USCG rating list (gocoastguard.com/careers/enlisted) and
# Wikipedia "List of United States Coast Guard ratings"
# Format matches O*NET return shape: "Title (Coast Guard - Enlisted/Officer)"
COAST_GUARD_RATINGS = {
    # Aviation group
    "AET": "Avionics Electrical Technician (Coast Guard - Enlisted)",
    "AMT": "Aviation Maintenance Technician (Coast Guard - Enlisted)",
    "AST": "Aviation Survival Technician (Coast Guard - Enlisted)",

    # Administrative & scientific
    "IS": "Intelligence Specialist (Coast Guard - Enlisted)",
    "IT": "Information Systems Technician (Coast Guard - Enlisted)",
    "PA": "Public Affairs Specialist (Coast Guard - Enlisted)",
    "SK": "Storekeeper (Coast Guard - Enlisted)",
    "YN": "Yeoman (Coast Guard - Enlisted)",

    # Deck & weapons group
    "BM": "Boatswain's Mate (Coast Guard - Enlisted)",
    "GM": "Gunner's Mate (Coast Guard - Enlisted)",
    "ME": "Maritime Enforcement Specialist (Coast Guard - Enlisted)",
    "MST": "Marine Science Technician (Coast Guard - Enlisted)",
    "OS": "Operations Specialist (Coast Guard - Enlisted)",

    # Engineering & hull group
    "DC": "Damage Controlman (Coast Guard - Enlisted)",
    "EM": "Electrician's Mate (Coast Guard - Enlisted)",
    "ET": "Electronics Technician (Coast Guard - Enlisted)",
    "MK": "Machinery Technician (Coast Guard - Enlisted)",

    # Medical & other
    "HS": "Health Services Technician (Coast Guard - Enlisted)",
    "CS": "Culinary Specialist (Coast Guard - Enlisted)",
    "DV": "Diver (Coast Guard - Enlisted)",
    "CMS": "Cyber Mission Specialist (Coast Guard - Enlisted)",
}


def _resolve_mos_title(branch: str, mos: str) -> str:
    """Look up the canonical military title for a (branch, mos) pair.

    Lookup priority:
    1. NAVY_OFFICER_DESIGNATORS (Navy officer codes — not in O*NET)
    2. COAST_GUARD_RATINGS (all CG codes — not in O*NET)
    3. O*NET exact match (Army, Marine, enlisted Navy/AF)
    4. O*NET prefix match (AF/USSF officer codes like 11F → 11F1B)

    Returns title string on success, empty string on miss. Cached 30 days.
    Empty string is a deliberate sentinel: prompt treats it as 'known unknown'
    and tells Haiku not to fabricate.
    """
    if not branch or not mos:
        return ""

    branch_norm = branch.lower()
    mos_norm = mos.upper()
    cache_key = f"mos_title:{branch_norm}:{mos_norm}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Priority 1: Navy officer designators (not in O*NET)
    if branch_norm == "navy" and mos_norm in NAVY_OFFICER_DESIGNATORS:
        title = NAVY_OFFICER_DESIGNATORS[mos_norm]
        cache.set(cache_key, title, MOS_TITLE_CACHE_TTL)
        return title

    # Priority 2: Coast Guard ratings (not in O*NET)
    if branch_norm == "coast_guard" and mos_norm in COAST_GUARD_RATINGS:
        title = COAST_GUARD_RATINGS[mos_norm]
        cache.set(cache_key, title, MOS_TITLE_CACHE_TTL)
        return title

    # Priority 3 & 4: O*NET lookup
    try:
        resp = http_requests.get(
            f"{ONET_V2_BASE}/veterans/military/",
            params={"keyword": mos, "branch": branch_norm},
            headers={
                "Accept": "application/json",
                "X-API-Key": settings.ONET_API_KEY,
            },
            timeout=10,
        )
    except http_requests.RequestException:
        logger.warning("O*NET title lookup network error for %s/%s", branch, mos)
        return ""

    if not resp.ok:
        cache.set(cache_key, "", MOS_TITLE_CACHE_TTL)
        return ""

    try:
        data = resp.json()
    except ValueError:
        return ""

    matches = data.get("military_match", [])

    # Priority 3: exact code match
    for match in matches:
        if match.get("code", "").upper() == mos_norm:
            title = match.get("title", "")
            cache.set(cache_key, title, MOS_TITLE_CACHE_TTL)
            return title

    # Priority 4: prefix match (Air Force / Space Force hierarchical codes)
    # User types "11F" — O*NET has 11F1B, 11F1C, 11F3A, etc.
    # Use first prefix hit but strip the sub-specialty from the title
    # (e.g. "Fighter Pilot, A-10" → "Fighter Pilot") to avoid over-specifying
    # a user's actual role.
    if branch_norm in {"air_force", "space_force"}:
        for match in matches:
            code = match.get("code", "").upper()
            if code.startswith(mos_norm) and len(code) > len(mos_norm):
                full_title = match.get("title", "")
                # Strip sub-specialty qualifier after comma
                # "Fighter Pilot, A-10 (Air Force - ...)" → "Fighter Pilot (Air Force - ...)"
                if ", " in full_title and " (" in full_title:
                    role, paren = full_title.split(" (", 1)
                    role = role.split(", ")[0]  # Drop everything after first comma
                    normalized = f"{role} ({paren}"
                else:
                    normalized = full_title
                cache.set(cache_key, normalized, MOS_TITLE_CACHE_TTL)
                return normalized

    # No match found — cache the miss to avoid retry churn
    cache.set(cache_key, "", MOS_TITLE_CACHE_TTL)
    return ""


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
