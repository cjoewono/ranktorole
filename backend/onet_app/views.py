import logging

import requests as http_requests
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from translate_app.throttles import OnetThrottle

logger = logging.getLogger(__name__)

ONET_BASE = "https://services.onetcenter.org/ws"


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
                headers={"Accept": "application/json"},
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
                        headers={"Accept": "application/json"},
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
