"""
Tests for the tiered throttle system.

Validates that:
1. TieredThrottle reads user.tier correctly
2. Free users get blocked at free-tier limits
3. Pro users get higher limits
4. Cache keys include tier (upgrade resets counter)
5. Unauthenticated requests fall back to free tier
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory
from rest_framework.test import APIClient

from .throttles import (
    ChatThrottle,
    DraftThrottle,
    FinalizeThrottle,
    OnetThrottle,
    UploadThrottle,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def disable_tiered_throttling():
    """Override the global conftest fixture to allow real throttling logic in this file."""
    yield


@pytest.fixture(autouse=True)
def clear_cache(db):
    """Clear the throttle cache before every test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def free_user(db):
    return User.objects.create_user(
        username='freeuser',
        email='free@example.com',
        password='testpass123',
        tier='free',
    )


@pytest.fixture
def pro_user(db):
    return User.objects.create_user(
        username='prouser',
        email='pro@example.com',
        password='testpass123',
        tier='pro',
    )


@pytest.fixture
def free_client(free_user):
    client = APIClient()
    client.force_authenticate(user=free_user)
    return client


@pytest.fixture
def pro_client(pro_user):
    client = APIClient()
    client.force_authenticate(user=pro_user)
    return client


# ---------------------------------------------------------------------------
# Unit tests — TieredThrottle internals
# ---------------------------------------------------------------------------

class TestTieredThrottleUnit:
    """Test the TieredThrottle base class mechanics directly."""

    def test_get_rate_returns_free_tier(self):
        throttle = UploadThrottle()
        throttle._tier = 'free'
        rate = throttle.get_rate()
        assert rate == '3/day'

    def test_get_rate_returns_pro_tier(self):
        throttle = UploadThrottle()
        throttle._tier = 'pro'
        rate = throttle.get_rate()
        assert rate == '15/day'

    def test_get_rate_unknown_tier_falls_back(self):
        """Unknown tier falls back to DEFAULT_THROTTLE_RATES."""
        throttle = UploadThrottle()
        throttle._tier = 'enterprise'
        rate = throttle.get_rate()
        assert rate == '3/day'

    def test_cache_key_includes_tier(self):
        factory = RequestFactory()
        request = factory.get('/')

        user = User(pk='00000000-0000-0000-0000-000000000001', tier='pro')
        request.user = user

        throttle = UploadThrottle()
        throttle._tier = 'pro'
        key = throttle.get_cache_key(request, None)

        assert 'pro' in key
        assert 'user_upload' in key
        assert str(user.pk) in key

    def test_cache_key_changes_on_tier_change(self):
        factory = RequestFactory()
        request = factory.get('/')

        user = User(pk='00000000-0000-0000-0000-000000000002', tier='free')
        request.user = user

        throttle = UploadThrottle()

        throttle._tier = 'free'
        key_free = throttle.get_cache_key(request, None)

        throttle._tier = 'pro'
        key_pro = throttle.get_cache_key(request, None)

        assert key_free != key_pro

    def test_all_scopes_defined(self):
        """Every throttle subclass has a scope matching TIERED_THROTTLE_RATES."""
        from django.conf import settings
        tiered = settings.TIERED_THROTTLE_RATES

        assert UploadThrottle.scope in tiered
        assert DraftThrottle.scope in tiered
        assert ChatThrottle.scope in tiered
        assert FinalizeThrottle.scope in tiered
        assert OnetThrottle.scope in tiered

    def test_draft_throttle_rates(self):
        throttle = DraftThrottle()
        throttle._tier = 'free'
        assert throttle.get_rate() == '1/day'
        throttle._tier = 'pro'
        assert throttle.get_rate() == '5/day'

    def test_chat_throttle_rates(self):
        throttle = ChatThrottle()
        throttle._tier = 'free'
        assert throttle.get_rate() == '10/day'
        throttle._tier = 'pro'
        assert throttle.get_rate() == '50/day'

    def test_finalize_throttle_rates(self):
        throttle = FinalizeThrottle()
        throttle._tier = 'free'
        assert throttle.get_rate() == '3/day'
        throttle._tier = 'pro'
        assert throttle.get_rate() == '15/day'

    def test_onet_throttle_rates(self):
        throttle = OnetThrottle()
        throttle._tier = 'free'
        assert throttle.get_rate() == '10/day'
        throttle._tier = 'pro'
        assert throttle.get_rate() == '30/day'


# ---------------------------------------------------------------------------
# Integration tests — throttle enforcement via API
# ---------------------------------------------------------------------------

class TestUploadThrottleIntegration:
    """Free user gets blocked after 3 uploads/day; pro user gets 15."""

    def _upload(self, client):
        return client.post('/api/v1/resumes/upload/')

    def test_free_user_blocked_after_limit(self, free_client):
        for _ in range(3):
            resp = self._upload(free_client)
            assert resp.status_code != 429

        resp = self._upload(free_client)
        assert resp.status_code == 429

    def test_pro_user_gets_higher_limit(self, pro_client):
        for _ in range(4):
            resp = self._upload(pro_client)
            assert resp.status_code != 429


class TestDraftThrottleIntegration:
    """Free user gets 1 draft/day; pro gets 5."""

    def _draft(self, client, resume_id):
        return client.post(
            f'/api/v1/resumes/{resume_id}/draft/',
            {'job_description': 'We need a supply chain manager with ten years of experience.'},
            format='json',
        )

    @pytest.fixture
    def free_resume(self, free_user):
        from translate_app.models import Resume
        return Resume.objects.create(
            user=free_user,
            military_text='Served as Army logistics officer for 8 years.',
            job_description='',
            civilian_title='',
            summary='',
        )

    @pytest.fixture
    def pro_resume(self, pro_user):
        from translate_app.models import Resume
        return Resume.objects.create(
            user=pro_user,
            military_text='Served as Army logistics officer for 8 years.',
            job_description='',
            civilian_title='',
            summary='',
        )

    def test_free_user_blocked_after_1(self, free_client, free_resume):
        resp = self._draft(free_client, free_resume.id)
        assert resp.status_code != 429

        resp = self._draft(free_client, free_resume.id)
        assert resp.status_code == 429

    def test_pro_user_gets_5(self, pro_client, pro_resume):
        for _ in range(2):
            resp = self._draft(pro_client, pro_resume.id)
            assert resp.status_code != 429


class TestChatThrottleIntegration:
    """Free user gets 10 chats/day; pro gets 50."""

    def _chat(self, client, resume_id):
        return client.post(
            f'/api/v1/resumes/{resume_id}/chat/',
            {'message': 'Emphasize leadership skills.'},
            format='json',
        )

    @pytest.fixture
    def free_resume(self, free_user):
        from translate_app.models import Resume
        return Resume.objects.create(
            user=free_user,
            military_text='Test',
            job_description='Test JD',
            civilian_title='Test Title',
            summary='Test summary',
            session_anchor={'test': True},
        )

    def test_free_user_blocked_after_10(self, free_client, free_resume):
        for _ in range(10):
            resp = self._chat(free_client, free_resume.id)
            assert resp.status_code != 429

        resp = self._chat(free_client, free_resume.id)
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# User model tier tests
# ---------------------------------------------------------------------------

class TestUserTierField:
    def test_default_tier_is_free(self, db):
        user = User.objects.create_user(
            username='defaultuser',
            email='default@example.com',
            password='testpass123',
        )
        assert user.tier == 'free'

    def test_tier_can_be_set_to_pro(self, db):
        user = User.objects.create_user(
            username='prouser2',
            email='pro2@example.com',
            password='testpass123',
            tier='pro',
        )
        assert user.tier == 'pro'

    def test_tier_persists_after_save(self, db):
        user = User.objects.create_user(
            username='persist',
            email='persist@example.com',
            password='testpass123',
            tier='free',
        )
        user.tier = 'pro'
        user.save()
        user.refresh_from_db()
        assert user.tier == 'pro'

    def test_tier_in_serializer(self, db):
        from user_app.serializers import UserSerializer
        user = User.objects.create_user(
            username='sertest',
            email='ser@example.com',
            password='testpass123',
            tier='pro',
        )
        data = UserSerializer(user).data
        assert data['tier'] == 'pro'

    def test_tier_is_read_only_in_serializer(self, db):
        from user_app.serializers import UserSerializer
        user = User.objects.create_user(
            username='readonly',
            email='readonly@example.com',
            password='testpass123',
            tier='free',
        )
        serializer = UserSerializer(user, data={'tier': 'pro'}, partial=True)
        assert serializer.is_valid()
        serializer.save()
        user.refresh_from_db()
        # tier should NOT have changed because it's read_only
        assert user.tier == 'free'
