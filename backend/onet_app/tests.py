"""Tests for O*NET proxy views."""

import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(
        username="reconuser", email="recon@test.com", password="testpass123"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class TestOnetSearchView:
    """Existing search endpoint — verify it still works."""

    def test_missing_keyword_returns_400(self, auth_client):
        resp = auth_client.get("/api/v1/onet/search/")
        assert resp.status_code == 400

    def test_with_keyword_returns_200(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"career": []}
            mock_get.return_value = mock_resp

            resp = auth_client.get("/api/v1/onet/search/?keyword=11B")
            assert resp.status_code == 200
            assert "occupations" in resp.data
            assert "skills" in resp.data


    def test_api_key_header_sent(self, auth_client):
        """Verify X-API-Key header is included in outbound O*NET requests."""
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"career": []}
            mock_get.return_value = mock_resp

            with patch("onet_app.views.settings") as mock_settings:
                mock_settings.ONET_API_KEY = "test-key-123"
                auth_client.get("/api/v1/onet/search/?keyword=medic")

            # Verify the header was passed
            call_args = mock_get.call_args
            assert call_args is not None
            headers = call_args[1].get("headers", {})
            assert "X-API-Key" in headers


class TestOnetMilitarySearchView:
    """Veterans military search endpoint."""

    def test_missing_keyword_returns_400(self, auth_client):
        resp = auth_client.get("/api/v1/onet/military/")
        assert resp.status_code == 400

    def test_successful_search(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"branch": "army", "code": "11B", "title": "Infantryman (Enlisted)", "active": True}
                ],
                "career": [
                    {
                        "code": "47-2061.00",
                        "title": "Construction Laborers",
                        "match_type": "some_duties",
                        "tags": {"bright_outlook": True},
                        "preparation_needed": "First term",
                        "pay_grade": "E1",
                    }
                ],
            }
            mock_get.return_value = mock_resp

            resp = auth_client.get("/api/v1/onet/military/?keyword=11B&branch=army")
            assert resp.status_code == 200
            assert len(resp.data["military_matches"]) == 1
            assert resp.data["military_matches"][0]["code"] == "11B"
            assert len(resp.data["careers"]) == 1
            assert resp.data["careers"][0]["code"] == "47-2061.00"
            assert resp.data["careers"][0]["match_type"] == "some_duties"

    def test_invalid_branch_defaults_to_all(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"career": []}
            mock_get.return_value = mock_resp

            resp = auth_client.get("/api/v1/onet/military/?keyword=11B&branch=invalid")
            assert resp.status_code == 200
            assert resp.data["branch"] == "all"

    def test_onet_api_failure_returns_empty(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = False
            mock_get.return_value = mock_resp

            resp = auth_client.get("/api/v1/onet/military/?keyword=11B")
            assert resp.status_code == 200
            assert resp.data["careers"] == []

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.get("/api/v1/onet/military/?keyword=11B")
        assert resp.status_code == 401


    def test_api_key_header_sent(self, auth_client):
        """Verify X-API-Key header is included in military search requests."""
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"career": [], "military_match": []}
            mock_get.return_value = mock_resp

            with patch("onet_app.views.settings") as mock_settings:
                mock_settings.ONET_API_KEY = "test-key-456"
                auth_client.get("/api/v1/onet/military/?keyword=11B")

            call_args = mock_get.call_args
            assert call_args is not None
            headers = call_args[1].get("headers", {})
            assert "X-API-Key" in headers


class TestOnetCareerDetailView:
    """Career detail aggregation endpoint."""

    def test_invalid_code_format_returns_400(self, auth_client):
        resp = auth_client.get("/api/v1/onet/career/invalid/")
        assert resp.status_code == 400

    def test_valid_code_format(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            def side_effect(url, **kwargs):
                mock = MagicMock()
                if "/skills" in url or "/knowledge" in url or "/technology" in url or "/outlook" in url:
                    mock.ok = True
                    mock.json.return_value = {}
                else:
                    mock.ok = True
                    mock.json.return_value = {
                        "title": "Construction Laborers",
                        "description": "Perform tasks at construction sites.",
                        "tags": {"bright_outlook": True},
                    }
                return mock
            mock_get.side_effect = side_effect

            resp = auth_client.get("/api/v1/onet/career/47-2061.00/")
            assert resp.status_code == 200
            assert resp.data["code"] == "47-2061.00"
            assert resp.data["title"] == "Construction Laborers"

    def test_not_found_returns_404(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = False
            mock_get.return_value = mock_resp

            resp = auth_client.get("/api/v1/onet/career/99-9999.00/")
            assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.get("/api/v1/onet/career/47-2061.00/")
        assert resp.status_code == 401

    def test_api_key_header_sent(self, auth_client):
        """Verify X-API-Key header is included in career detail requests."""
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"title": "Test", "description": "Test", "tags": {}}
            mock_get.return_value = mock_resp

            with patch("onet_app.views.settings") as mock_settings:
                mock_settings.ONET_API_KEY = "test-key-789"
                auth_client.get("/api/v1/onet/career/47-2061.00/")

            call_args = mock_get.call_args
            assert call_args is not None
            headers = call_args[1].get("headers", {})
            assert "X-API-Key" in headers


class TestReconEnrichView:
    """POST /api/v1/onet/enrich/ — Claude Haiku enrichment endpoint."""

    def test_missing_onet_code_returns_400(self, auth_client):
        resp = auth_client.post("/api/v1/onet/enrich/", {}, format="json")
        assert resp.status_code == 400

    def test_invalid_onet_code_format_returns_400(self, auth_client):
        resp = auth_client.post(
            "/api/v1/onet/enrich/", {"onet_code": "invalid"}, format="json"
        )
        assert resp.status_code == 400

    def test_no_profile_context_returns_400(self, auth_client):
        resp = auth_client.post(
            "/api/v1/onet/enrich/", {"onet_code": "47-2061.00"}, format="json"
        )
        assert resp.status_code == 400
        assert "profile" in resp.data["error"].lower()

    def test_successful_enrichment(self, db):
        from onet_app.schemas import CareerEnrichment

        user = User.objects.create_user(
            username="enrichuser",
            email="enrich@test.com",
            password="testpass123",
            profile_context={
                "branch": "Army",
                "mos": "11B",
                "skills": ["Leadership", "Logistics"],
            },
        )
        client = APIClient()
        client.force_authenticate(user=user)

        mock_enrichment = CareerEnrichment(
            match_score=72,
            personalized_description="As an Army 11B Infantryman, your leadership "
            "experience translates directly to construction site supervision roles.",
            skill_gaps=["OSHA 30-Hour Card", "PMP certification"],
            education_recommendation="Consider a BS in Construction Management via GI Bill.",
            transferable_skills=[
                "Team leadership",
                "Risk assessment",
                "Equipment operation",
                "Safety protocols",
            ],
        )

        with patch("onet_app.views.http_requests.get") as mock_onet:
            def onet_side_effect(url, **kwargs):
                mock = MagicMock()
                mock.ok = True
                mock.status_code = 200
                if "/skills" in url:
                    mock.json.return_value = [{"element": [{"name": "Active Listening"}]}]
                elif "/knowledge" in url:
                    mock.json.return_value = [{"element": [{"name": "Building and Construction"}]}]
                elif "/technology" in url:
                    mock.json.return_value = []
                elif "/job_outlook" in url:
                    mock.json.return_value = {
                        "salary": {
                            "annual_median": "40000",
                            "annual_10th_percentile": "30000",
                            "annual_90th_percentile": "55000",
                        }
                    }
                else:
                    mock.json.return_value = {
                        "title": "Construction Laborers",
                        "what_they_do": "Perform tasks at construction sites.",
                    }
                return mock
            mock_onet.side_effect = onet_side_effect

            with patch("onet_app.views.enrich_career") as mock_enrich:
                mock_enrich.return_value = mock_enrichment

                resp = client.post(
                    "/api/v1/onet/enrich/",
                    {"onet_code": "47-2061.00"},
                    format="json",
                )

                assert resp.status_code == 200
                assert resp.data["onet_code"] == "47-2061.00"
                assert resp.data["career_title"] == "Construction Laborers"
                assert resp.data["enrichment"]["match_score"] == 72
                assert len(resp.data["enrichment"]["transferable_skills"]) == 4
                assert "OSHA 30-Hour Card" in resp.data["enrichment"]["skill_gaps"]

    def test_onet_404_returns_404(self, db):
        user = User.objects.create_user(
            username="enrich404",
            email="enrich404@test.com",
            password="testpass123",
            profile_context={"branch": "Navy", "mos": "IT"},
        )
        client = APIClient()
        client.force_authenticate(user=user)

        with patch("onet_app.views.http_requests.get") as mock_onet:
            mock_resp = MagicMock()
            mock_resp.ok = False
            mock_resp.status_code = 404
            mock_onet.return_value = mock_resp

            resp = client.post(
                "/api/v1/onet/enrich/",
                {"onet_code": "99-9999.99"},
                format="json",
            )
            assert resp.status_code == 404

    def test_haiku_failure_returns_503(self, db):
        user = User.objects.create_user(
            username="enrichfail",
            email="enrichfail@test.com",
            password="testpass123",
            profile_context={"branch": "Navy", "mos": "IT"},
        )
        client = APIClient()
        client.force_authenticate(user=user)

        with patch("onet_app.views.http_requests.get") as mock_onet:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"title": "Test", "what_they_do": "Test"}
            mock_onet.return_value = mock_resp

            with patch("onet_app.views.enrich_career") as mock_enrich:
                mock_enrich.return_value = None

                resp = client.post(
                    "/api/v1/onet/enrich/",
                    {"onet_code": "47-2061.00"},
                    format="json",
                )
                assert resp.status_code == 503

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.post(
            "/api/v1/onet/enrich/", {"onet_code": "47-2061.00"}, format="json"
        )
        assert resp.status_code == 401


class TestReconEnrichCacheAndCeiling:
    """Cost-control tests: caching + global daily ceiling."""

    def test_cache_hit_skips_llm_call(self, db):
        from django.core.cache import cache
        from onet_app.recon_enrich_service import enrich_career
        from onet_app.schemas import CareerEnrichment

        cache.clear()

        career_data = {
            "code": "47-2061.00",
            "title": "Construction Laborers",
            "description": "Test",
            "skills": [],
            "knowledge": [],
            "outlook": {},
        }
        profile_context = {"branch": "Army", "mos": "11B", "skills": ["Leadership"]}

        mock_result = CareerEnrichment(
            match_score=72,
            personalized_description="Test description.",
            skill_gaps=["Test gap"],
            education_recommendation="Test edu.",
            transferable_skills=["Test skill 1", "Test skill 2", "Test skill 3", "Test skill 4"],
        )

        with patch("onet_app.recon_enrich_service._resolve_mos_title") as mock_resolve, \
             patch("onet_app.recon_enrich_service._call_haiku_typed") as mock_haiku:
            mock_resolve.return_value = "Infantryman (Army - Enlisted)"
            mock_haiku.return_value = mock_result

            result1 = enrich_career(career_data, profile_context)
            assert result1 is not None
            assert mock_haiku.call_count == 1

            result2 = enrich_career(career_data, profile_context)
            assert result2 is not None
            assert result2.match_score == 72
            assert mock_haiku.call_count == 1  # still 1, no new call

        cache.clear()

    def test_different_profile_invalidates_cache(self, db):
        from django.core.cache import cache
        from onet_app.recon_enrich_service import enrich_career
        from onet_app.schemas import CareerEnrichment

        cache.clear()

        career_data = {
            "code": "47-2061.00", "title": "Test", "description": "",
            "skills": [], "knowledge": [], "outlook": {},
        }
        profile_a = {"branch": "Army", "mos": "11B", "skills": ["Leadership"]}
        profile_b = {"branch": "Navy", "mos": "IT", "skills": ["Networking"]}

        mock_result = CareerEnrichment(
            match_score=72,
            personalized_description="Test.",
            skill_gaps=["Gap"],
            education_recommendation="Edu.",
            transferable_skills=["s1", "s2", "s3", "s4"],
        )

        with patch("onet_app.recon_enrich_service._resolve_mos_title") as mock_resolve, \
             patch("onet_app.recon_enrich_service._call_haiku_typed") as mock_haiku:
            mock_resolve.return_value = "Test Title (Army - Enlisted)"
            mock_haiku.return_value = mock_result

            enrich_career(career_data, profile_a)
            enrich_career(career_data, profile_b)

            assert mock_haiku.call_count == 2

        cache.clear()

    def test_global_ceiling_returns_none(self, db, settings):
        from django.core.cache import cache
        from onet_app.recon_enrich_service import enrich_career

        cache.clear()

        settings.RECON_ENRICH_DAILY_CEILING = 1

        career_data = {
            "code": "47-2061.00", "title": "Test", "description": "",
            "skills": [], "knowledge": [], "outlook": {},
        }
        profile_a = {"branch": "Army", "mos": "11B", "skills": ["A"]}
        profile_b = {"branch": "Navy", "mos": "IT", "skills": ["B"]}

        from onet_app.schemas import CareerEnrichment
        mock_result = CareerEnrichment(
            match_score=50, personalized_description="T.",
            skill_gaps=["g"], education_recommendation="e.",
            transferable_skills=["1", "2", "3", "4"],
        )

        with patch("onet_app.recon_enrich_service._resolve_mos_title") as mock_resolve, \
             patch("onet_app.recon_enrich_service._call_haiku_typed") as mock_haiku:
            mock_resolve.return_value = "Test Title (Army - Enlisted)"
            mock_haiku.return_value = mock_result

            result1 = enrich_career(career_data, profile_a)
            assert result1 is not None
            assert mock_haiku.call_count == 1

            result2 = enrich_career(career_data, profile_b)
            assert result2 is None
            assert mock_haiku.call_count == 1

        cache.clear()


class TestResolveMosTitle:
    """Tests for the MOS title resolver (O*NET veterans/military lookup)."""

    def test_returns_title_on_exact_match(self, db):
        """Successful O*NET response with matching code returns title."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "11B", "title": "Infantryman (Army - Enlisted)", "branch": "army"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Army", "11B")
            assert title == "Infantryman (Army - Enlisted)"

        cache.clear()

    def test_returns_empty_on_no_match(self, db):
        """O*NET returns matches but none are exact code — empty string."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "99Z", "title": "Something Else", "branch": "army"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Army", "11B")
            assert title == ""

        cache.clear()

    def test_returns_cached_result_on_second_call(self, db):
        """Second call with same (branch, mos) hits cache, not O*NET."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "11B", "title": "Infantryman (Army - Enlisted)", "branch": "army"},
                ],
            }
            mock_get.return_value = mock_resp

            t1 = _resolve_mos_title("Army", "11B")
            t2 = _resolve_mos_title("Army", "11B")

            assert t1 == "Infantryman (Army - Enlisted)"
            assert t2 == t1
            assert mock_get.call_count == 1  # Second call cached

        cache.clear()

    def test_navy_officer_designator_uses_local_lookup(self, db):
        """Navy 1110 resolves via local dict without hitting O*NET."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            title = _resolve_mos_title("Navy", "1110")

        assert title == "Surface Warfare Officer (Navy - Officer)"
        # O*NET should not have been called — local dict hit
        assert mock_get.call_count == 0

        cache.clear()

    def test_navy_enlisted_falls_back_to_onet(self, db):
        """Navy IT (enlisted) isn't in local dict — should hit O*NET."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "IT", "title": "Information Systems Technician (Navy - Enlisted)", "branch": "navy"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Navy", "IT")

        assert title == "Information Systems Technician (Navy - Enlisted)"
        assert mock_get.call_count == 1  # Did hit O*NET

        cache.clear()

    def test_coast_guard_rating_uses_local_lookup(self, db):
        """CG BM (Boatswain's Mate) resolves via local dict, no O*NET call."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            title = _resolve_mos_title("Coast_Guard", "BM")

        assert title == "Boatswain's Mate (Coast Guard - Enlisted)"
        assert mock_get.call_count == 0

        cache.clear()

    def test_coast_guard_unknown_rating_returns_empty(self, db):
        """CG rating not in dict falls through — O*NET returns empty → empty."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"military_match": []}
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Coast_Guard", "ZZ")

        assert title == ""

        cache.clear()

    def test_air_force_prefix_match_strips_sub_specialty(self, db):
        """AF 11F user input matches O*NET's 11F1B, returns generic title."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "11F1B", "title": "Fighter Pilot, A-10 (Air Force - Commissioned Officer only)"},
                    {"code": "11F1C", "title": "Fighter Pilot, F-15 (Air Force - Commissioned Officer only)"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Air_Force", "11F")

        assert title == "Fighter Pilot (Air Force - Commissioned Officer only)"

        cache.clear()

    def test_af_exact_match_wins_over_prefix(self, db):
        """When O*NET returns exact code match, prefix-match doesn't run."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "21A1", "title": "Aircraft Maintenance Sub-specialty (Air Force - Commissioned Officer only)"},
                    {"code": "21A", "title": "Aircraft Maintenance (Air Force - Commissioned Officer only)"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Air_Force", "21A")

        assert title == "Aircraft Maintenance (Air Force - Commissioned Officer only)"

        cache.clear()

    def test_army_unchanged_behavior(self, db):
        """Army uses O*NET exact match — verify no regression from new code paths."""
        from django.core.cache import cache
        from onet_app.recon_enrich_service import _resolve_mos_title

        cache.clear()

        with patch("onet_app.recon_enrich_service.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [
                    {"code": "11B", "title": "Infantryman (Army - Enlisted)"},
                ],
            }
            mock_get.return_value = mock_resp

            title = _resolve_mos_title("Army", "11B")

        assert title == "Infantryman (Army - Enlisted)"

        cache.clear()
