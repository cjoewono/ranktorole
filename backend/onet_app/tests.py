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
