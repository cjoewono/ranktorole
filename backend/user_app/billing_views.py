"""Billing endpoints — Checkout, Customer Portal, Status, Webhook."""
from __future__ import annotations

import logging

import stripe
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .billing_services import (
    create_checkout_session,
    create_portal_session,
    verify_webhook,
)
from .billing_throttles import CheckoutThrottle
from .models import SubscriptionAuditLog, User

logger = logging.getLogger(__name__)

_STATUS_TO_TIER = {
    'active': 'pro',
    'trialing': 'pro',
    'past_due': 'pro',     # grace — still pro until canceled
    'incomplete': 'free',
    'incomplete_expired': 'free',
    'canceled': 'free',
    'unpaid': 'free',
    'inactive': 'free',
}


def _is_allowed_return_url(url: str) -> bool:
    """Restrict return_url to our production domain or local dev.

    Prevents an authenticated user from redirecting the Stripe portal exit
    to an attacker-controlled domain.
    """
    if not url or not isinstance(url, str):
        return False
    if url.startswith('https://ranktorole.net/'):
        return True
    if url.startswith('http://localhost:'):
        return True
    return False


class CheckoutSessionView(APIView):
    """POST /api/v1/billing/checkout/ — create a Stripe Checkout Session."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [CheckoutThrottle]

    def post(self, request: Request) -> Response:
        try:
            session = create_checkout_session(request.user)
        except stripe.error.StripeError:
            logger.exception("Stripe checkout session creation failed")
            return Response(
                {"detail": "Billing service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(session, status=status.HTTP_200_OK)


class PortalSessionView(APIView):
    """POST /api/v1/billing/portal/ — Stripe Customer Portal URL."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [CheckoutThrottle]

    def post(self, request: Request) -> Response:
        return_url = request.data.get('return_url') or 'http://localhost:5173/profile'

        if not _is_allowed_return_url(return_url):
            return Response(
                {"detail": "Invalid return_url."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = create_portal_session(request.user, return_url)
        except stripe.error.StripeError:
            logger.exception("Stripe portal session create failed")
            return Response(
                {"detail": "Billing service unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(session, status=status.HTTP_200_OK)


class BillingStatusView(APIView):
    """GET /api/v1/billing/status/ — expose billing state to the frontend."""
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        u = request.user
        from django.conf import settings as _s
        limits = {
            **_s.FREE_TIER_DAILY_LIMITS,
            'chat_turn_count_per_resume': _s.FREE_TIER_CHAT_LIMIT,
        }
        return Response({
            'tier': u.tier,
            'subscription_status': u.subscription_status,
            'usage': {
                'resume_tailor_count': u.resume_tailor_count,
                'last_reset_date': u.last_reset_date,
            },
            'limits': limits if u.tier != 'pro' else None,
        })


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """POST /api/v1/billing/webhook/ — Stripe event receiver.

    Signature verification is mandatory; no DB work happens before construct_event.
    """
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: Request) -> Response:
        payload = request.body
        sig = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        try:
            event = verify_webhook(payload, sig)
        except ValueError as e:
            logger.warning("Webhook ValueError: %r | payload_len=%d | sig_present=%s", e, len(payload), bool(sig))
            return Response({"detail": "Invalid payload."}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            logger.warning("Webhook SignatureVerificationError: %r | payload_len=%d", e, len(payload))
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        event_id = event.get('id', '')
        event_type = event.get('type', '')

        # Idempotency — ignore replays of the same event.
        if SubscriptionAuditLog.objects.filter(stripe_event_id=event_id).exists():
            return Response({"received": True, "duplicate": True}, status=status.HTTP_200_OK)

        try:
            if event_type == 'checkout.session.completed':
                _handle_checkout_completed(event)
            elif event_type == 'customer.subscription.deleted':
                _handle_subscription_deleted(event)
            elif event_type in ('customer.subscription.updated', 'customer.subscription.created'):
                _handle_subscription_updated(event)
            # Other events are acknowledged but not processed
        except Exception:
            logger.exception("Webhook processing failed for event %s", event_id)
            # Return 500 so Stripe retries — safe because we're idempotent above
            return Response({"detail": "Processing error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"received": True}, status=status.HTTP_200_OK)


def _resolve_user(*, customer_id: str = '', user_id: str = '') -> User | None:
    if user_id:
        user = User.objects.filter(pk=user_id).first()
        if user:
            return user
    if customer_id:
        return User.objects.filter(stripe_customer_id=customer_id).first()
    return None


def _apply_status(user: User, new_status: str, event_id: str, event_type: str) -> None:
    """Atomically update status + tier + write audit log. Idempotent by event_id."""
    with transaction.atomic():
        locked = User.objects.select_for_update().get(pk=user.pk)
        previous = locked.subscription_status
        new_tier = _STATUS_TO_TIER.get(new_status, 'free')
        if previous == new_status and locked.tier == new_tier:
            # State unchanged — still log for full audit trail
            SubscriptionAuditLog.objects.create(
                user=locked,
                previous_status=previous,
                new_status=new_status,
                stripe_event_id=event_id,
                event_type=event_type,
            )
            return
        locked.subscription_status = new_status
        locked.tier = new_tier
        locked.save(update_fields=['subscription_status', 'tier', 'updated_at'])
        SubscriptionAuditLog.objects.create(
            user=locked,
            previous_status=previous,
            new_status=new_status,
            stripe_event_id=event_id,
            event_type=event_type,
        )


def _handle_checkout_completed(event: dict) -> None:
    data = event['data']['object']
    customer_id = data.get('customer', '')
    user_id = (data.get('metadata') or {}).get('user_id') or data.get('client_reference_id', '')
    user = _resolve_user(customer_id=customer_id, user_id=user_id)
    if not user:
        logger.warning("checkout.session.completed for unknown user (customer=%s)", customer_id)
        return
    if not user.stripe_customer_id and customer_id:
        user.stripe_customer_id = customer_id
        user.save(update_fields=['stripe_customer_id', 'updated_at'])
    _apply_status(user, 'active', event['id'], event['type'])


def _handle_subscription_updated(event: dict) -> None:
    data = event['data']['object']
    customer_id = data.get('customer', '')
    new_status = data.get('status', 'inactive')
    user = _resolve_user(customer_id=customer_id)
    if not user:
        return
    _apply_status(user, new_status, event['id'], event['type'])


def _handle_subscription_deleted(event: dict) -> None:
    data = event['data']['object']
    customer_id = data.get('customer', '')
    user = _resolve_user(customer_id=customer_id)
    if not user:
        return
    _apply_status(user, 'canceled', event['id'], event['type'])
