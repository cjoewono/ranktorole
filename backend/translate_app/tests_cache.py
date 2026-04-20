"""Tests for resume list caching and write-path invalidation.

Verifies the cache-aside pattern:
- First GET hits DB
- Second GET serves from cache
- Create / update / delete invalidate the cache
- Per-user isolation: User A's writes don't invalidate User B's cache
"""

import pytest
from io import BytesIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from translate_app.models import Resume
from translate_app.cache_utils import resume_list_cache_key

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache_before_test():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        username="usera", email="a@test.com", password="testpass123"
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        username="userb", email="b@test.com", password="testpass123"
    )


@pytest.fixture
def client_a(user_a):
    client = APIClient()
    client.force_authenticate(user=user_a)
    return client


@pytest.fixture
def client_b(user_b):
    client = APIClient()
    client.force_authenticate(user=user_b)
    return client


def _make_resume(user, **kwargs):
    defaults = {
        "military_text": "test military text",
        "job_description": "",
        "civilian_title": "",
        "summary": "",
    }
    defaults.update(kwargs)
    return Resume.objects.create(user=user, **defaults)


class TestResumeListCache:
    def test_first_call_populates_cache(self, client_a, user_a):
        _make_resume(user_a)
        cache_key = resume_list_cache_key(user_a)

        assert cache.get(cache_key) is None
        resp = client_a.get("/api/v1/resumes/")
        assert resp.status_code == 200
        assert cache.get(cache_key) is not None

    def test_second_call_serves_from_cache(self, client_a, user_a):
        _make_resume(user_a)
        client_a.get("/api/v1/resumes/")

        # Manually mutate cache to prove cache (not DB) is being read
        cache.set(resume_list_cache_key(user_a), [{"id": "fake", "civilian_title": "FROM_CACHE"}], 60)

        resp = client_a.get("/api/v1/resumes/")
        assert resp.status_code == 200
        assert resp.data == [{"id": "fake", "civilian_title": "FROM_CACHE"}]

    def test_user_isolation(self, client_a, client_b, user_a, user_b):
        """User B's cache key is independent from User A's."""
        _make_resume(user_a)
        _make_resume(user_b)

        client_a.get("/api/v1/resumes/")
        client_b.get("/api/v1/resumes/")

        assert cache.get(resume_list_cache_key(user_a)) is not None
        assert cache.get(resume_list_cache_key(user_b)) is not None
        assert cache.get(resume_list_cache_key(user_a)) != cache.get(resume_list_cache_key(user_b))


class TestResumeListInvalidation:
    def test_upload_invalidates_cache(self, client_a, user_a):
        """Uploading a new resume must invalidate the user's list cache."""
        _make_resume(user_a)
        client_a.get("/api/v1/resumes/")
        assert cache.get(resume_list_cache_key(user_a)) is not None

        # Mock pdf extraction to avoid needing a real PDF
        fake_pdf = BytesIO(b"%PDF-1.4 fake content")
        fake_pdf.name = "test.pdf"

        with patch("translate_app.views.extract_pdf_text", return_value="extracted text"):
            resp = client_a.post(
                "/api/v1/resumes/upload/",
                {"file": fake_pdf},
                format="multipart",
            )

        assert resp.status_code == 201
        assert cache.get(resume_list_cache_key(user_a)) is None

    def test_delete_invalidates_cache(self, client_a, user_a):
        resume = _make_resume(user_a)
        client_a.get("/api/v1/resumes/")
        assert cache.get(resume_list_cache_key(user_a)) is not None

        resp = client_a.delete(f"/api/v1/resumes/{resume.id}/")
        assert resp.status_code == 204
        assert cache.get(resume_list_cache_key(user_a)) is None

    def test_user_a_write_does_not_invalidate_user_b_cache(
        self, client_a, client_b, user_a, user_b
    ):
        """Critical isolation: A's create must not touch B's cached list."""
        _make_resume(user_b)
        client_b.get("/api/v1/resumes/")
        assert cache.get(resume_list_cache_key(user_b)) is not None

        fake_pdf = BytesIO(b"%PDF-1.4 fake content")
        fake_pdf.name = "test.pdf"

        with patch("translate_app.views.extract_pdf_text", return_value="text"):
            client_a.post(
                "/api/v1/resumes/upload/",
                {"file": fake_pdf},
                format="multipart",
            )

        # B's cache must still be intact
        assert cache.get(resume_list_cache_key(user_b)) is not None

    def test_cache_returns_fresh_data_after_invalidation(self, client_a, user_a):
        """After invalidation, next GET must reflect the new state."""
        _make_resume(user_a)
        resp1 = client_a.get("/api/v1/resumes/")
        assert len(resp1.data) == 1

        fake_pdf = BytesIO(b"%PDF-1.4 fake content")
        fake_pdf.name = "test.pdf"

        with patch("translate_app.views.extract_pdf_text", return_value="text"):
            client_a.post(
                "/api/v1/resumes/upload/",
                {"file": fake_pdf},
                format="multipart",
            )

        resp2 = client_a.get("/api/v1/resumes/")
        assert len(resp2.data) == 2, "List must reflect newly-created resume"
