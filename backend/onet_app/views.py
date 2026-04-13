import logging
import re as re_module

import requests as http_requests
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from translate_app.throttles import OnetThrottle

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


class OnetSearchView(APIView):
    """GET /api/v1/onet/search/?keyword={mos_code}

    Proxies to O*NET Web Services. Returns related occupation titles
    and key skills/competencies for a military occupation code.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [OnetThrottle]

    def get(self, request):
        keyword = request.query_params.get("keyword", "").strip()
        if not keyword:
            return Response(
                {"error": "keyword query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Search for matching occupations
            search_resp = http_requests.get(
                f"{ONET_BASE}/mnm/search",
                params={"keyword": keyword},
                headers=_onet_headers(),
                auth=_onet_auth(),
                timeout=10,
            )
            if not search_resp.ok:
                return Response(
                    {"occupations": [], "skills": []},
                    status=status.HTTP_200_OK,
                )

            data = search_resp.json()
            careers = data.get("career", [])

            # Extract occupation codes and titles
            occupations = []
            all_skills = set()

            # Take top 3 matches
            for career in careers[:3]:
                code = career.get("code", "")
                title = career.get("title", "")
                occupations.append({"code": code, "title": title})

                # Fetch skills for this occupation
                if code:
                    skills_resp = http_requests.get(
                        f"{ONET_BASE}/online/occupations/{code}/summary/skills",
                        headers=_onet_headers(),
                        auth=_onet_auth(),
                        timeout=10,
                    )
                    if skills_resp.ok:
                        skills_data = skills_resp.json()
                        for element in skills_data.get("element", []):
                            skill_name = element.get("name", "")
                            if skill_name:
                                all_skills.add(skill_name)

            return Response(
                {
                    "occupations": occupations,
                    "skills": sorted(all_skills),
                }
            )

        except http_requests.RequestException:
            logger.error("O*NET API request failed")
            return Response(
                {"occupations": [], "skills": []},
                status=status.HTTP_200_OK,
            )


class OnetMilitarySearchView(APIView):
    """GET /api/v1/onet/military/?keyword={mos_code}&branch={branch}

    Proxies to O*NET My Next Move for Veterans military search.
    Returns civilian career matches ranked by relevance.

    Query params:
        keyword (required): MOS code or military job title (e.g., "11B", "Infantryman")
        branch (optional): Service branch filter. Values: army, navy, air_force,
                           marine_corps, coast_guard. Default: all.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [OnetThrottle]

    VALID_BRANCHES = {"army", "navy", "air_force", "marine_corps", "coast_guard", "all"}

    def get(self, request):
        keyword = request.query_params.get("keyword", "").strip()
        if not keyword:
            return Response(
                {"error": "keyword query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        branch = request.query_params.get("branch", "all").strip().lower()
        if branch not in self.VALID_BRANCHES:
            branch = "all"

        try:
            params = {"keyword": keyword}
            if branch != "all":
                params["branch"] = branch

            resp = http_requests.get(
                f"{ONET_BASE}/veterans/military/",
                params=params,
                headers=_onet_headers(),
                auth=_onet_auth(),
                timeout=15,
            )

            if not resp.ok:
                return Response(
                    {"military_matches": [], "careers": []},
                    status=status.HTTP_200_OK,
                )

            data = resp.json()

            # Extract military matches
            military_matches = []
            raw_matches = data.get("military_match", [])
            if isinstance(raw_matches, dict):
                raw_matches = [raw_matches]
            for m in raw_matches:
                military_matches.append({
                    "branch": m.get("branch", ""),
                    "code": m.get("code", ""),
                    "title": m.get("title", ""),
                    "active": m.get("active", True),
                })

            # Extract civilian career matches
            careers = []
            for career in data.get("career", []):
                careers.append({
                    "code": career.get("code", ""),
                    "title": career.get("title", ""),
                    "match_type": career.get("match_type", ""),
                    "tags": career.get("tags", {}),
                    "preparation_needed": career.get("preparation_needed", ""),
                    "pay_grade": career.get("pay_grade", ""),
                })

            return Response({
                "keyword": keyword,
                "branch": branch,
                "military_matches": military_matches,
                "careers": careers,
            })

        except http_requests.RequestException:
            logger.error("O*NET Veterans military search failed")
            return Response(
                {"military_matches": [], "careers": []},
                status=status.HTTP_200_OK,
            )


class OnetCareerDetailView(APIView):
    """GET /api/v1/onet/career/{onet_code}/

    Aggregates multiple O*NET data points for a single occupation code.
    Fetches: overview, skills, knowledge, technology, and job outlook.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [OnetThrottle]

    # Validate O*NET-SOC format: XX-XXXX.XX
    ONET_CODE_PATTERN = re_module.compile(r'^\d{2}-\d{4}\.\d{2}$')

    def _fetch_json(self, url):
        """Helper: GET a URL, return parsed JSON or empty dict on failure."""
        try:
            resp = http_requests.get(
                url,
                headers=_onet_headers(),
                auth=_onet_auth(),
                timeout=10,
            )
            if resp.ok:
                return resp.json()
        except http_requests.RequestException:
            pass
        return {}

    def get(self, request, onet_code):
        if not self.ONET_CODE_PATTERN.match(onet_code):
            return Response(
                {"error": "Invalid O*NET-SOC code format. Expected XX-XXXX.XX"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base = f"{ONET_BASE}/veterans/careers/{onet_code}"

        # Fetch overview (career report root)
        overview_data = self._fetch_json(f"{base}/")
        if not overview_data:
            return Response(
                {"error": "Occupation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Fetch supplementary data
        skills_data = self._fetch_json(f"{base}/skills")
        knowledge_data = self._fetch_json(f"{base}/knowledge")
        technology_data = self._fetch_json(f"{base}/technology")
        outlook_data = self._fetch_json(f"{base}/job_outlook")

        # Extract skills list — v2 returns a list of categories, each with sub-elements
        skills = []
        for category in (skills_data if isinstance(skills_data, list) else []):
            for elem in category.get("element", []):
                name = elem.get("name", "")
                if name:
                    skills.append({"name": name, "description": ""})

        # Extract knowledge list — same v2 shape as skills
        knowledge = []
        for category in (knowledge_data if isinstance(knowledge_data, list) else []):
            for elem in category.get("element", []):
                name = elem.get("name", "")
                if name:
                    knowledge.append({"name": name, "description": ""})

        # Extract technology items — v2 returns list directly; title is a string; examples use "title" key
        technology = []
        for cat in (technology_data if isinstance(technology_data, list) else technology_data.get("category", [])):
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

        # Extract outlook
        outlook = {}
        if outlook_data:
            outlook = {
                "category": outlook_data.get("outlook", {}).get("category", ""),
                "description": outlook_data.get("outlook", {}).get("description", ""),
            }
            salary = outlook_data.get("salary", {})
            if salary:
                outlook["salary"] = {
                    "annual_median": salary.get("annual_median", ""),
                    "annual_10th": salary.get("annual_10th_percentile", ""),
                    "annual_90th": salary.get("annual_90th_percentile", ""),
                }

        return Response({
            "code": onet_code,
            "title": overview_data.get("title", ""),
            "description": overview_data.get("what_they_do", overview_data.get("description", "")),
            "tags": overview_data.get("tags", {}),
            "skills": skills,
            "knowledge": knowledge,
            "technology": technology,
            "outlook": outlook,
        })
