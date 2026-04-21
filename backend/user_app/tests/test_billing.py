"""Tests for Stripe billing: checkout, webhook, permissions, audit log."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import stripe
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from user_app.models import SubscriptionAuditLog

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='billuser', email='bill@example.com', password='pw12345!x'
    )


@pytest.fixture
def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

class TestCheckoutEndpoint:
    @patch('user_app.billing_views.create_checkout_session')
    def test_returns_url(self, mock_create, auth_client):
        mock_create.return_value = {'id': 'cs_test', 'url': 'https://checkout.stripe.com/c/test'}
        r = auth_client.post('/api/v1/billing/checkout/')
        assert r.status_code == 200
        assert r.data['url'].startswith('https://checkout.stripe.com/')

    def test_unauthenticated_401(self, db):
        r = APIClient().post('/api/v1/billing/checkout/')
        assert r.status_code == 401

    @patch('user_app.billing_views.create_checkout_session')
    def test_stripe_failure_returns_503(self, mock_create, auth_client):
        mock_create.side_effect = stripe.error.APIConnectionError('down')
        r = auth_client.post('/api/v1/billing/checkout/')
        assert r.status_code == 503


# ---------------------------------------------------------------------------
# Webhook signature + handlers
# ---------------------------------------------------------------------------

def _event(type_: str, user_id: str = '', customer_id: str = 'cus_123', sub_status: str = 'active', event_id: str = 'evt_1'):
    obj = {'customer': customer_id}
    if type_ == 'checkout.session.completed':
        obj.update({'metadata': {'user_id': user_id}, 'client_reference_id': user_id})
    elif type_.startswith('customer.subscription'):
        obj['status'] = sub_status
    return {'id': event_id, 'type': type_, 'data': {'object': obj}}


class TestStripeWebhook:
    def test_invalid_signature_rejected(self, db):
        r = APIClient().post(
            '/api/v1/billing/webhook/',
            data=b'{}', content_type='application/json',
            HTTP_STRIPE_SIGNATURE='bogus',
        )
        assert r.status_code == 400

    @patch('user_app.billing_views.verify_webhook')
    def test_checkout_completed_upgrades_user(self, mock_verify, user):
        user.stripe_customer_id = 'cus_abc'
        user.save()
        mock_verify.return_value = _event(
            'checkout.session.completed', user_id=str(user.id), customer_id='cus_abc', event_id='evt_chk_1'
        )
        r = APIClient().post(
            '/api/v1/billing/webhook/',
            data=b'{}', content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig',
        )
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.tier == 'pro'
        assert user.subscription_status == 'active'
        assert SubscriptionAuditLog.objects.filter(user=user, new_status='active').count() == 1

    @patch('user_app.billing_views.verify_webhook')
    def test_subscription_deleted_downgrades_user(self, mock_verify, user):
        user.stripe_customer_id = 'cus_abc'
        user.tier = 'pro'
        user.subscription_status = 'active'
        user.save()
        mock_verify.return_value = _event(
            'customer.subscription.deleted', customer_id='cus_abc', event_id='evt_del_1'
        )
        r = APIClient().post(
            '/api/v1/billing/webhook/',
            data=b'{}', content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig',
        )
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.tier == 'free'
        assert user.subscription_status == 'canceled'
        log = SubscriptionAuditLog.objects.get(user=user, stripe_event_id='evt_del_1')
        assert log.previous_status == 'active'
        assert log.new_status == 'canceled'

    @patch('user_app.billing_views.verify_webhook')
    def test_replayed_event_is_idempotent(self, mock_verify, user):
        user.stripe_customer_id = 'cus_abc'
        user.save()
        mock_verify.return_value = _event(
            'checkout.session.completed', user_id=str(user.id), customer_id='cus_abc', event_id='evt_replay'
        )
        APIClient().post('/api/v1/billing/webhook/', data=b'{}', content_type='application/json', HTTP_STRIPE_SIGNATURE='sig')
        r2 = APIClient().post('/api/v1/billing/webhook/', data=b'{}', content_type='application/json', HTTP_STRIPE_SIGNATURE='sig')
        assert r2.status_code == 200
        assert r2.data.get('duplicate') is True
        assert SubscriptionAuditLog.objects.filter(stripe_event_id='evt_replay').count() == 1

    @patch('user_app.billing_views.verify_webhook')
    def test_subscription_updated_transitions_status(self, mock_verify, user):
        """customer.subscription.updated moves user through status transitions per _STATUS_TO_TIER."""
        user.stripe_customer_id = 'cus_abc'
        user.tier = 'pro'
        user.subscription_status = 'active'
        user.save()

        # Transition 1: active → past_due. User stays Pro (grace period).
        mock_verify.return_value = _event(
            'customer.subscription.updated',
            customer_id='cus_abc',
            sub_status='past_due',
            event_id='evt_upd_1',
        )
        r1 = APIClient().post(
            '/api/v1/billing/webhook/',
            data=b'{}', content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig',
        )
        assert r1.status_code == 200
        user.refresh_from_db()
        assert user.subscription_status == 'past_due'
        assert user.tier == 'pro', 'past_due must remain Pro per _STATUS_TO_TIER grace period'

        log1 = SubscriptionAuditLog.objects.get(stripe_event_id='evt_upd_1')
        assert log1.previous_status == 'active'
        assert log1.new_status == 'past_due'
        assert log1.event_type == 'customer.subscription.updated'

        # Transition 2: past_due → canceled via .updated. User flips to Free.
        mock_verify.return_value = _event(
            'customer.subscription.updated',
            customer_id='cus_abc',
            sub_status='canceled',
            event_id='evt_upd_2',
        )
        r2 = APIClient().post(
            '/api/v1/billing/webhook/',
            data=b'{}', content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig',
        )
        assert r2.status_code == 200
        user.refresh_from_db()
        assert user.subscription_status == 'canceled'
        assert user.tier == 'free'

        log2 = SubscriptionAuditLog.objects.get(stripe_event_id='evt_upd_2')
        assert log2.previous_status == 'past_due'
        assert log2.new_status == 'canceled'


# ---------------------------------------------------------------------------
# Portal return_url allowlist
# ---------------------------------------------------------------------------

class TestPortalAllowlist:
    def test_portal_rejects_external_return_url(self, auth_client):
        r = auth_client.post(
            '/api/v1/billing/portal/',
            data={'return_url': 'https://phishing.example.com/landing'},
            format='json',
        )
        assert r.status_code == 400

    def test_portal_rejects_http_production_url(self, auth_client):
        r = auth_client.post(
            '/api/v1/billing/portal/',
            data={'return_url': 'http://ranktorole.app/profile'},
            format='json',
        )
        assert r.status_code == 400

    def test_portal_rejects_javascript_url(self, auth_client):
        r = auth_client.post(
            '/api/v1/billing/portal/',
            data={'return_url': 'javascript:alert(1)'},
            format='json',
        )
        assert r.status_code == 400

    @patch('user_app.billing_views.create_portal_session')
    def test_portal_accepts_production_https_url(self, mock_portal, auth_client):
        mock_portal.return_value = {'url': 'https://billing.stripe.com/p/session/abc'}
        r = auth_client.post(
            '/api/v1/billing/portal/',
            data={'return_url': 'https://ranktorole.app/profile'},
            format='json',
        )
        assert r.status_code == 200

    @patch('user_app.billing_views.create_portal_session')
    def test_portal_accepts_localhost_url(self, mock_portal, auth_client):
        mock_portal.return_value = {'url': 'https://billing.stripe.com/p/session/abc'}
        r = auth_client.post(
            '/api/v1/billing/portal/',
            data={'return_url': 'http://localhost:5173/profile'},
            format='json',
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Billing status
# ---------------------------------------------------------------------------

class TestBillingStatus:
    def test_free_user_sees_limits(self, auth_client, user):
        r = auth_client.get('/api/v1/billing/status/')
        assert r.status_code == 200
        assert r.data['tier'] == 'free'
        assert r.data['limits'] is not None
        assert 'resume_tailor_count' in r.data['limits']
        assert 'chat_turn_count_per_resume' in r.data['limits']
        # chat turns are now tracked per-resume, not on the user
        assert 'chat_turn_count' not in r.data['usage']

    def test_pro_user_sees_no_limits(self, auth_client, user):
        user.tier = 'pro'
        user.subscription_status = 'active'
        user.save()
        r = auth_client.get('/api/v1/billing/status/')
        assert r.data['tier'] == 'pro'
        assert r.data['limits'] is None


# ---------------------------------------------------------------------------
# Permissions: IsProOrUnderLimit (daily reset)
# ---------------------------------------------------------------------------

class TestDailyCounterReset:
    def test_stale_last_reset_date_zeroes_counters_on_next_use(self, user, auth_client, db):
        """resume_tailor_count resets when last_reset_date is stale."""
        from datetime import date, timedelta
        user.resume_tailor_count = 999
        user.last_reset_date = date.today() - timedelta(days=2)
        user.save()

        from translate_app.tests import (
            _DRAFT_PAYLOAD,
            _create_resume,
            _make_mock_translation,
        )
        resume = _create_resume(user)
        with patch('translate_app.views.call_claude_draft') as mock_draft:
            mock_draft.return_value = _make_mock_translation(_DRAFT_PAYLOAD)
            r = auth_client.post(
                f'/api/v1/resumes/{resume.id}/draft/',
                {'job_description': 'We need a supply chain manager with 5+ years.'},
                format='json',
            )
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.resume_tailor_count == 1  # reset to 0 then bumped to 1
        assert user.last_reset_date == timezone.now().date()
