"""Stripe API wrapper — Checkout Sessions, Customer Portal, webhook signature.

Separating SDK calls from views keeps secrets + retry semantics in one place and
makes mocking in tests trivial.
"""
from __future__ import annotations

import logging
import uuid

import stripe
from django.conf import settings

logger = logging.getLogger(__name__)


def _configure():
    """Configure SDK at call-time so tests that monkeypatch settings work."""
    stripe.api_key = settings.STRIPE_SECRET_KEY


def get_or_create_customer(user) -> str:
    """Return the user's stripe_customer_id, creating one if needed.

    Uses an idempotency key derived from user.id so a network retry never
    produces duplicate Stripe customers.
    """
    _configure()
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        metadata={'user_id': str(user.id)},
        idempotency_key=f'create-customer-{user.id}',
    )
    user.stripe_customer_id = customer['id']
    user.save(update_fields=['stripe_customer_id', 'updated_at'])
    return customer['id']


def create_checkout_session(user) -> dict:
    """Create a Checkout Session for the Pro subscription.

    - automatic_tax enabled for regional tax compliance (VAT/sales tax)
    - Idempotency key bound to a fresh UUID per call so a user CAN start a new
      session after canceling, but a network retry within a single client action
      does not produce two sessions (client passes the same token on retry via
      SDK transport layer semantics).
    """
    _configure()
    customer_id = get_or_create_customer(user)
    idempotency_key = f'checkout-{user.id}-{uuid.uuid4()}'

    session = stripe.checkout.Session.create(
        mode='subscription',
        customer=customer_id,
        line_items=[{'price': settings.STRIPE_PRICE_ID, 'quantity': 1}],
        success_url=settings.STRIPE_CHECKOUT_SUCCESS_URL,
        cancel_url=settings.STRIPE_CHECKOUT_CANCEL_URL,
        automatic_tax={'enabled': True},
        customer_update={'address': 'auto'},
        allow_promotion_codes=True,
        client_reference_id=str(user.id),
        metadata={'user_id': str(user.id)},
        idempotency_key=idempotency_key,
    )
    return {'id': session['id'], 'url': session['url']}


def create_portal_session(user, return_url: str) -> dict:
    """Create a Customer Portal session so users can manage or cancel."""
    _configure()
    customer_id = get_or_create_customer(user)
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
        idempotency_key=f'portal-{user.id}-{uuid.uuid4()}',
    )
    return {'url': session['url']}


def verify_webhook(payload: bytes, signature_header: str):
    """Cryptographically verify a webhook payload. Raises on failure."""
    _configure()
    return stripe.Webhook.construct_event(
        payload, signature_header, settings.STRIPE_WEBHOOK_SECRET
    )
