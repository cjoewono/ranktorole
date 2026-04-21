"""
Recon brainstorm service.

Pipeline: form inputs → O*NET baseline crosswalks (one call per service entry,
deduped) → Haiku ranks and picks top 3 → we fetch full detail on #1 → we return
one detailed card + two slim runner-up cards.

Reuses shared infrastructure from onet_app:
- _resolve_mos_title()                — canonical MOS title lookup
- _check_and_increment_global_ceiling — atomic cross-worker daily spend cap
- _call_haiku_typed()                 — Pydantic-validated Haiku call
- strip_tags                          — stored-XSS defense on LLM strings
- _normalize_career_data()            — O*NET v2 response normalizer
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Optional

import requests as http_requests
from django.core.cache import cache

from onet_app.recon_enrich_service import (
    _call_haiku_typed,
    _check_and_increment_global_ceiling,
    _resolve_mos_title,
)
from onet_app.views import (
    ONET_BASE,
    _normalize_career_data,
    _onet_headers,
)
from translate_app.services import strip_tags

from .schemas import BrainstormCandidate, BrainstormRanking

logger = logging.getLogger(__name__)

ONET_CODE_PATTERN = re.compile(r"^\d{2}-\d{4}\.\d{2}$")
BASELINE_MAX_CAREERS = 20
BASELINE_PER_SERVICE_CAP = 10
BRAINSTORM_CACHE_TTL = 7 * 24 * 60 * 60  # 7 days


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

def _cache_key(form: dict) -> str:
    """Stable SHA256 of the normalized form. Profile-independent by design."""

    def _norm_list(items: list) -> list:
        return sorted(s.strip().lower() for s in items if s and s.strip())

    services_norm = sorted(
        f"{s['branch'].strip()}|{s['mos_code'].strip().upper()}"
        for s in form.get("services", [])
    )
    parts = [
        "|".join(services_norm),
        form.get("grade", "").strip(),
        form.get("position", "").strip().lower(),
        form.get("target_career_field", "").strip().lower(),
        ",".join(_norm_list(form.get("education", []))),
        ",".join(_norm_list(form.get("certifications", []))),
        ",".join(_norm_list(form.get("licenses", []))),
        form.get("state", "").strip().lower(),
    ]
    digest = hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"recon_brainstorm:{digest}"


# ---------------------------------------------------------------------------
# O*NET baseline
# ---------------------------------------------------------------------------

def _fetch_baseline_for_service(branch: str, mos_code: str) -> list:
    """Fetch civilian career crosswalks for a single (branch, mos_code) pair.

    Returns a list of career dicts (deduped by onet_code). Empty list on failure.
    """
    params = {"keyword": mos_code}
    if branch.lower().replace(" ", "_") != "all":
        params["branch"] = branch.lower().replace(" ", "_")

    try:
        resp = http_requests.get(
            f"{ONET_BASE}/veterans/military/",
            params=params,
            headers=_onet_headers(),
            timeout=10,
        )
        if not resp.ok:
            logger.warning(
                "O*NET baseline miss branch=%s mos=%s status=%s",
                branch, mos_code, resp.status_code,
            )
            return []
        data = resp.json()
    except http_requests.RequestException:
        logger.warning("O*NET baseline exception branch=%s mos=%s", branch, mos_code)
        return []

    careers_by_code: dict = {}
    raw_careers = data.get("careers", {}).get("career", []) or data.get("career", [])
    for c in raw_careers[:BASELINE_PER_SERVICE_CAP]:
        code = c.get("code", "")
        if not ONET_CODE_PATTERN.match(code):
            continue
        careers_by_code[code] = {
            "code": code,
            "title": c.get("title", ""),
            "match_type": c.get("tags", {}).get("match_type", "keyword"),
            "tags": c.get("tags", {}),
        }
    return list(careers_by_code.values())


def _build_merged_baseline(form: dict) -> list:
    """Merge crosswalks from all service entries, dedupe, cap at BASELINE_MAX_CAREERS."""
    merged: dict = {}
    for svc in form.get("services", []):
        entries = _fetch_baseline_for_service(svc["branch"], svc["mos_code"])
        for entry in entries:
            existing = merged.get(entry["code"])
            if existing is None or _match_strength(entry["match_type"]) > _match_strength(existing["match_type"]):
                merged[entry["code"]] = entry
    result = list(merged.values())
    result.sort(key=lambda c: _match_strength(c["match_type"]), reverse=True)
    return result[:BASELINE_MAX_CAREERS]


def _match_strength(match_type: str) -> int:
    return {"most_duties": 3, "some_duties": 2, "crosswalk": 1, "keyword": 0}.get(match_type, 0)


# ---------------------------------------------------------------------------
# Career detail fetch
# ---------------------------------------------------------------------------

def _fetch_json(url: str) -> dict:
    try:
        resp = http_requests.get(url, headers=_onet_headers(), timeout=10)
        if resp.ok:
            return resp.json()
    except http_requests.RequestException:
        pass
    return {}


def _fetch_full_detail(onet_code: str) -> Optional[dict]:
    """Fetch full O*NET career report. Returns normalized dict or None on failure."""
    base = f"{ONET_BASE}/veterans/careers/{onet_code}"
    overview = _fetch_json(f"{base}/")
    if not overview:
        return None
    skills = _fetch_json(f"{base}/skills")
    knowledge = _fetch_json(f"{base}/knowledge")
    technology = _fetch_json(f"{base}/technology")
    outlook = _fetch_json(f"{base}/job_outlook")
    normalized = _normalize_career_data(overview, skills, knowledge, technology, outlook)
    normalized["code"] = onet_code
    return normalized


# ---------------------------------------------------------------------------
# Haiku prompt
# ---------------------------------------------------------------------------

def _resolve_all_mos_titles(services: list) -> list:
    """Resolve canonical titles for every (branch, mos) pair. Empty string on miss."""
    lines = []
    for svc in services:
        title = _resolve_mos_title(svc["branch"], svc["mos_code"])
        if title:
            lines.append(f"- {svc['branch']} {svc['mos_code']} — {title}")
        else:
            lines.append(
                f"- {svc['branch']} {svc['mos_code']} (specific duties not verified — do not invent)"
            )
    return lines


def _build_prompt(form: dict, baseline: list) -> str:
    """Build the Haiku prompt. Grounds the model in the baseline so it cannot invent codes."""
    mos_lines = _resolve_all_mos_titles(form["services"])

    baseline_lines = [
        f"- {c['code']}: {c['title']} (match_type={c['match_type']})"
        for c in baseline
    ]

    def _list_line(label: str, items: list, fallback: str = "Not specified") -> str:
        return f"- {label}: {', '.join(items) if items else fallback}"

    return (
        "You are an exploratory career transition counselor for US military veterans. "
        "Evaluate the ONET_BASELINE list against the VETERAN_PROFILE and return the "
        "top 3 careers ranked by compatibility.\n\n"
        "VETERAN_PROFILE:\n"
        + "\n".join(mos_lines) + "\n"
        + f"- Grade: {form.get('grade') or 'Not specified'}\n"
        + f"- Position: {form.get('position') or 'Not specified'}\n"
        + f"- Target Career Field: {form.get('target_career_field') or 'Open to options'}\n"
        + _list_line("Education", form.get("education", [])) + "\n"
        + _list_line("Certifications", form.get("certifications", [])) + "\n"
        + _list_line("Licenses", form.get("licenses", [])) + "\n"
        + f"- State: {form.get('state') or 'Not specified'}\n\n"
        + "ONET_BASELINE (pick onet_code values ONLY from this list):\n"
        + "\n".join(baseline_lines) + "\n\n"
        + "CRITICAL RULES:\n"
        + "- onet_code MUST match one of the codes in ONET_BASELINE exactly. Do NOT invent codes.\n"
        + "- Do NOT invent duties, programs, or experience the veteran did not list.\n"
        + "- If an MOS line is marked 'do not invent', do not fabricate duties from the code.\n"
        + "- match_rationale: 2-3 sentences grounded in the form inputs. Reference specific "
        + "education, certs, or MOS titles by name when relevant.\n"
        + "- skill_gaps: 2-4 concrete gaps the veteran may need to close. Real certifications or "
        + "skills only.\n"
        + "- transferable_skills: 3-5 skills from the veteran's background that apply. Concrete, "
        + "not platitudes like 'leadership.'\n"
        + "- Return ONLY a JSON object matching this schema:\n"
        + json.dumps(BrainstormRanking.model_json_schema(), indent=2) + "\n"
    )


# ---------------------------------------------------------------------------
# Degraded fallback
# ---------------------------------------------------------------------------

def _strongest_baseline_pick(baseline: list) -> Optional[dict]:
    """Return the strongest O*NET crosswalk from the baseline, or None if empty."""
    if not baseline:
        return None
    return baseline[0]


def _degraded_response(baseline: list) -> Optional[dict]:
    """Build a degraded response using the strongest O*NET crosswalk. None if baseline empty."""
    pick = _strongest_baseline_pick(baseline)
    if pick is None:
        return None
    detail = _fetch_full_detail(pick["code"])
    if detail is None:
        return None
    detail["reasoning"] = None
    return {
        "best_match": detail,
        "also_consider": [],
        "degraded": True,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_brainstorm(form: dict) -> Optional[dict]:
    """Execute the brainstorm pipeline. Return response dict, or None on total failure.

    None means: O*NET baseline could not be fetched for any service entry. Caller
    should return 502. Every other failure mode falls back to degraded mode.
    """
    cache_key = _cache_key(form)
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info("run_brainstorm cache_hit key=%s", cache_key)
        return cached

    baseline = _build_merged_baseline(form)
    if not baseline:
        logger.warning("run_brainstorm baseline_empty services=%s", form.get("services"))
        return None

    if not _check_and_increment_global_ceiling():
        logger.warning("run_brainstorm ceiling_hit — returning degraded")
        degraded = _degraded_response(baseline)
        if degraded is not None:
            cache.set(cache_key, degraded, BRAINSTORM_CACHE_TTL)
        return degraded

    prompt = _build_prompt(form, baseline)
    try:
        ranking = _call_haiku_typed(
            [{"role": "user", "content": prompt}],
            BrainstormRanking,
        )
    except Exception:
        logger.exception("run_brainstorm haiku_failed")
        degraded = _degraded_response(baseline)
        if degraded is not None:
            cache.set(cache_key, degraded, BRAINSTORM_CACHE_TTL)
        return degraded

    baseline_codes = {c["code"] for c in baseline}
    valid_picks: list = [
        c for c in ranking.candidates if c.onet_code in baseline_codes
    ]
    if not valid_picks:
        logger.warning("run_brainstorm haiku_picks_all_invalid — returning degraded")
        degraded = _degraded_response(baseline)
        if degraded is not None:
            cache.set(cache_key, degraded, BRAINSTORM_CACHE_TTL)
        return degraded

    winner = valid_picks[0]
    detail = _fetch_full_detail(winner.onet_code)
    if detail is None:
        logger.warning("run_brainstorm detail_fetch_failed code=%s", winner.onet_code)
        degraded = _degraded_response(baseline)
        if degraded is not None:
            cache.set(cache_key, degraded, BRAINSTORM_CACHE_TTL)
        return degraded

    detail["reasoning"] = {
        "match_score": winner.match_score,
        "match_rationale": strip_tags(winner.match_rationale),
        "skill_gaps": [strip_tags(s) for s in winner.skill_gaps],
        "transferable_skills": [strip_tags(s) for s in winner.transferable_skills],
    }

    also_consider = [
        {
            "code": c.onet_code,
            "title": next(
                (b["title"] for b in baseline if b["code"] == c.onet_code),
                "",
            ),
            "match_score": c.match_score,
            "match_rationale": strip_tags(c.match_rationale),
        }
        for c in valid_picks[1:3]
    ]

    response = {
        "best_match": detail,
        "also_consider": also_consider,
        "degraded": False,
    }
    cache.set(cache_key, response, BRAINSTORM_CACHE_TTL)
    return response
