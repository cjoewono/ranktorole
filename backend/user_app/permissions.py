"""Tier-based access control.

Two separate permissions:

- IsProOrUnderLimit: gates endpoints backed by a DAILY-RESET counter on the User
  (currently resume_tailor_count). Views opt in with:

      counter_field     = 'resume_tailor_count'
      counter_limit_key = 'resume_tailor_count'   # key into FREE_TIER_DAILY_LIMITS

- ChatTurnLimit: gates chat against a PERMANENT per-resume counter
  (resume.chat_turn_count vs settings.FREE_TIER_CHAT_LIMIT).
  Reads the Resume via the view's get_user_resume() helper + URL pk.

Pro users (subscription_status ∈ PRO_STATUSES and tier == 'pro') bypass both.
"""
from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

PRO_STATUSES = {'active', 'trialing', 'past_due'}


def _is_pro(user) -> bool:
    return user.subscription_status in PRO_STATUSES and user.tier == 'pro'


def _reset_if_new_day(user) -> None:
    """Zero daily counters if last_reset_date is stale. Race-safe."""
    today = timezone.now().date()
    if user.last_reset_date == today:
        return
    with transaction.atomic():
        updated = type(user).objects.filter(
            pk=user.pk,
        ).exclude(last_reset_date=today).update(
            resume_tailor_count=0,
            last_reset_date=today,
        )
    if updated:
        user.resume_tailor_count = 0
        user.last_reset_date = today


def bump_counter(user, counter_field: str) -> None:
    """Atomically increment a daily user counter. Call after a successful AI call."""
    _reset_if_new_day(user)
    type(user).objects.filter(pk=user.pk).update(**{counter_field: F(counter_field) + 1})
    setattr(user, counter_field, getattr(user, counter_field) + 1)


_LIMIT_CODES = {
    'resume_tailor_count': (
        'TAILOR_LIMIT_REACHED',
        "You've reached the {limit} tailor limit. Upgrade to Pro for more.",
    ),
}


class IsProOrUnderLimit(BasePermission):
    """Deny when a free user has hit a daily-resetting per-user quota."""

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False

        _reset_if_new_day(user)

        if _is_pro(user):
            return True

        counter_field = getattr(view, 'counter_field', None)
        limit_key = getattr(view, 'counter_limit_key', counter_field)
        if not counter_field or not limit_key:
            return True

        limit = settings.FREE_TIER_DAILY_LIMITS.get(limit_key)
        if limit is None:
            return True
        if getattr(user, counter_field, 0) < limit:
            return True

        code, template = _LIMIT_CODES.get(
            counter_field,
            ('LIMIT_REACHED', "You've reached your daily limit of {limit}. Upgrade to Pro for more."),
        )
        raise PermissionDenied(detail={
            'detail': template.format(limit=limit),
            'code': code,
        })


class ChatTurnLimit(BasePermission):
    """Deny when a free user's per-resume permanent chat counter is at limit.

    Expects the view to expose `get_user_resume(pk, user)` (already present on
    translate_app views) and URL kwarg 'pk'. If the resume cannot be located,
    this permission defers — the view's own 404 handling runs.
    """

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if _is_pro(user):
            return True

        pk = view.kwargs.get('pk')
        get_resume = getattr(view, 'get_user_resume', None) or globals().get('_resolve_resume')
        # Views use a module-level helper; fall back to translate_app's get_user_resume.
        if get_resume is None:
            try:
                from translate_app.views import get_user_resume as get_resume
            except Exception:
                return True
        resume = get_resume(pk, user)
        if resume is None:
            # Defer to the view for a clean 404 instead of leaking existence via 403.
            return True

        limit = settings.FREE_TIER_CHAT_LIMIT
        if resume.chat_turn_count < limit:
            return True

        raise PermissionDenied(detail={
            'detail': f"You've reached the {limit} message limit. Upgrade to Pro for unlimited chat.",
            'code': 'CHAT_LIMIT_REACHED',
        })
