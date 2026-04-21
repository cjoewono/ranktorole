"""
Tiered throttle classes for RankToRole.

Each endpoint gets a throttle that reads the authenticated user's `tier` field
and selects the matching rate from TIERED_THROTTLE_RATES in settings.

Cache key format: throttle_{scope}_{tier}_{user_pk} (authenticated) or throttle_{scope}_{tier}_{ip} (anonymous)
This ensures free and pro users get independent rate counters.
"""

from django.conf import settings
from rest_framework.throttling import UserRateThrottle


class TieredThrottle(UserRateThrottle):
    """
    Base class for tier-aware throttling.

    Subclasses set `scope` (e.g. 'user_upload'). At runtime, the throttle
    reads `request.user.tier` and looks up the rate from
    settings.TIERED_THROTTLE_RATES[scope][tier].

    Falls back to settings.DEFAULT_THROTTLE_RATES[scope] if the tier
    lookup fails (e.g. unauthenticated request hitting a throttled view).
    """

    # Subclasses MUST set this
    scope = None

    def get_rate(self):
        """Return the rate string (e.g. '3/day') for the current user's tier."""
        tier = getattr(self, '_tier', 'free')
        tiered_rates = getattr(settings, 'TIERED_THROTTLE_RATES', {})
        scope_rates = tiered_rates.get(self.scope, {})

        if tier in scope_rates:
            return scope_rates[tier]

        # Fallback to flat DEFAULT_THROTTLE_RATES
        return super().get_rate()

    def allow_request(self, request, view):
        """Capture the user's tier before the rate check runs."""
        user = request.user
        if user.is_authenticated:
            self._tier = getattr(user, 'tier', 'free')
        else:
            self._tier = 'free'

        # Re-parse rate for this tier (DRF caches rate on __init__)
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        """
        Include tier in the cache key so upgrading a user immediately
        gives them the higher limit without waiting for cache expiry.

        NOTE: Downgrade also resets the counter (fresh free bucket).
        Acceptable for MVP where tier changes are admin-only. When a
        self-service billing flow is added, clear the user's throttle
        cache keys on tier change to prevent gaming.
        """
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        tier = getattr(self, '_tier', 'free')
        return f'throttle_{self.scope}_{tier}_{ident}'


class UploadThrottle(TieredThrottle):
    scope = 'user_upload'


class DraftThrottle(TieredThrottle):
    scope = 'user_draft'


class ChatThrottle(TieredThrottle):
    scope = 'user_chat'


class FinalizeThrottle(TieredThrottle):
    scope = 'user_finalize'


class OnetThrottle(TieredThrottle):
    scope = 'user_onet'


class ReconEnrichThrottle(TieredThrottle):
    scope = 'user_recon_brainstorm'


from rest_framework.views import exception_handler
from rest_framework.exceptions import Throttled


def tiered_throttle_exception_handler(exc, context):
    """
    Replaces DRF's default 429 payload with a structured body so the
    frontend can route to a tier-aware daily-limit modal.

    Falls back to DRF's default handler for all other exceptions.
    """
    response = exception_handler(exc, context)

    if isinstance(exc, Throttled) and response is not None:
        wait_seconds = int(exc.wait) if exc.wait is not None else None
        response.data = {
            'code': 'DAILY_LIMIT_REACHED',
            'detail': str(exc.detail) if hasattr(exc, 'detail') else 'Daily limit reached.',
            'retry_after_seconds': wait_seconds,
        }

    return response
