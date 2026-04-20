"""Tests for O*NET response caching layer.

Verifies:
- First call hits upstream (mocked http_requests.get)
- Second call serves from cache (zero upstream calls)
- Failed/empty responses are NOT cached
- Different query params produce different cache keys
"""

import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(
        username="cacheuser",
        email="cache@test.com",
        password="testpass123",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture(autouse=True)
def clear_cache_before_test():
    cache.clear()
    yield
    cache.clear()


class TestOnetSearchViewCache:
    def test_first_call_hits_upstream(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "career": [{"code": "11-9199.00", "title": "Test Manager"}]
            }
            mock_get.return_value = mock_resp

            resp = auth_client.get("/api/v1/onet/search/?keyword=11B")
            assert resp.status_code == 200
            assert mock_get.call_count >= 1

    def test_second_call_serves_from_cache(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "career": [{"code": "11-9199.00", "title": "Test Manager"}]
            }
            mock_get.return_value = mock_resp

            auth_client.get("/api/v1/onet/search/?keyword=11B")
            first_call_count = mock_get.call_count

            resp2 = auth_client.get("/api/v1/onet/search/?keyword=11B")
            assert resp2.status_code == 200
            assert mock_get.call_count == first_call_count, "Second call should be served from cache"

    def test_different_keywords_produce_different_cache_keys(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "career": [{"code": "11-9199.00", "title": "Manager"}]
            }
            mock_get.return_value = mock_resp

            auth_client.get("/api/v1/onet/search/?keyword=11B")
            calls_after_first = mock_get.call_count

            auth_client.get("/api/v1/onet/search/?keyword=25B")
            assert mock_get.call_count > calls_after_first, "Different keyword should miss cache"

    def test_empty_results_not_cached(self, auth_client):
        """Empty upstream responses should not poison the cache."""
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"career": []}
            mock_get.return_value = mock_resp

            auth_client.get("/api/v1/onet/search/?keyword=ZZZ")
            calls_after_first = mock_get.call_count

            auth_client.get("/api/v1/onet/search/?keyword=ZZZ")
            assert mock_get.call_count > calls_after_first, "Empty result should not be cached"


class TestOnetMilitarySearchViewCache:
    def test_second_call_serves_from_cache(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [{"branch": "army", "code": "11B", "title": "Infantry"}],
                "career": [],
            }
            mock_get.return_value = mock_resp

            auth_client.get("/api/v1/onet/military/?keyword=11B&branch=army")
            first_call_count = mock_get.call_count

            resp2 = auth_client.get("/api/v1/onet/military/?keyword=11B&branch=army")
            assert resp2.status_code == 200
            assert mock_get.call_count == first_call_count

    def test_different_branches_miss_cache(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {
                "military_match": [{"branch": "army", "code": "11B", "title": "Infantry"}],
                "career": [],
            }
            mock_get.return_value = mock_resp

            auth_client.get("/api/v1/onet/military/?keyword=11B&branch=army")
            calls_after_first = mock_get.call_count

            auth_client.get("/api/v1/onet/military/?keyword=11B&branch=navy")
            assert mock_get.call_count > calls_after_first


class TestOnetCareerDetailViewCache:
    def test_second_call_serves_from_cache(self, auth_client):
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.json.return_value = {"title": "Construction Manager", "what_they_do": "Manage stuff"}
            mock_get.return_value = mock_resp

            auth_client.get("/api/v1/onet/career/47-2061.00/")
            first_call_count = mock_get.call_count

            resp2 = auth_client.get("/api/v1/onet/career/47-2061.00/")
            assert resp2.status_code == 200
            assert mock_get.call_count == first_call_count

    def test_404_not_cached(self, auth_client):
        """A 404 from upstream should not be cached."""
        with patch("onet_app.views.http_requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.ok = False
            mock_resp.json.return_value = {}
            mock_get.return_value = mock_resp

            resp = auth_client.get("/api/v1/onet/career/99-9999.99/")
            assert resp.status_code == 404
            calls_after_first = mock_get.call_count

            auth_client.get("/api/v1/onet/career/99-9999.99/")
            assert mock_get.call_count > calls_after_first
