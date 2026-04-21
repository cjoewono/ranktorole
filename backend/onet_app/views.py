"""
O*NET HTTP utilities.

After the Recon rebuild (April 2026), this module no longer exposes any views.
It is a support library for recon_app and onet_app.recon_enrich_service:

- ONET_BASE           — base URL for O*NET v2 API
- _onet_headers()     — X-API-Key header builder
- _normalize_career_data() — parses raw v2 responses into a consistent shape

All public O*NET endpoints have been removed. The only Recon surface is
POST /api/v1/recon/brainstorm/ (recon_app).
"""

import logging

import requests as http_requests
from django.conf import settings

logger = logging.getLogger(__name__)

ONET_BASE = "https://api-v2.onetcenter.org"


def _onet_headers():
    """Shared headers for all O*NET v2 API requests."""
    return {
        "Accept": "application/json",
        "X-API-Key": settings.ONET_API_KEY,
    }


def _onet_auth():
    """Return HTTP Basic Auth tuple for O*NET Web Services, or None if unconfigured."""
    if settings.ONET_USERNAME and settings.ONET_PASSWORD:
        return (settings.ONET_USERNAME, settings.ONET_PASSWORD)
    return None


def _normalize_career_data(
    overview_data: dict,
    skills_data,
    knowledge_data,
    technology_data,
    outlook_data: dict,
) -> dict:
    """Normalize raw O*NET v2 responses into a consistent career_data dict."""
    skills = []
    for category in (skills_data if isinstance(skills_data, list) else []):
        for elem in category.get("element", []):
            name = elem.get("name", "")
            if name:
                skills.append({"name": name, "description": ""})

    knowledge = []
    for category in (knowledge_data if isinstance(knowledge_data, list) else []):
        for elem in category.get("element", []):
            name = elem.get("name", "")
            if name:
                knowledge.append({"name": name, "description": ""})

    technology = []
    _tech_list = technology_data if isinstance(technology_data, list) else (
        technology_data.get("category", []) if isinstance(technology_data, dict) else []
    )
    for cat in _tech_list:
        raw_title = cat.get("title", "")
        cat_title = raw_title if isinstance(raw_title, str) else raw_title.get("name", "")
        examples = []
        for ex in cat.get("example", []):
            ex_name = ex.get("title", ex.get("name", ""))
            hot = ex.get("hot_technology", False)
            if ex_name:
                examples.append({"name": ex_name, "hot": hot})
        if cat_title:
            technology.append({"category": cat_title, "examples": examples})

    outlook = {}
    if outlook_data and isinstance(outlook_data, dict):
        outlook_section = outlook_data.get("outlook") or {}
        if not isinstance(outlook_section, dict):
            outlook_section = {}
        outlook = {
            "category": outlook_section.get("category", ""),
            "description": outlook_section.get("description", ""),
        }
        salary = outlook_data.get("salary") or {}
        if salary and isinstance(salary, dict):
            outlook["salary"] = {
                "annual_median": salary.get("annual_median", ""),
                "annual_10th": salary.get("annual_10th_percentile", ""),
                "annual_90th": salary.get("annual_90th_percentile", ""),
            }

    return {
        "title": overview_data.get("title", ""),
        "description": overview_data.get("what_they_do", overview_data.get("description", "")),
        "tags": overview_data.get("tags", {}),
        "skills": skills,
        "knowledge": knowledge,
        "technology": technology,
        "outlook": outlook,
    }
