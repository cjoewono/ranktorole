"""Cache key builders and invalidation helpers for resume list caching.

Cache-aside pattern: ResumeListView reads from cache, falling back to DB
on miss. All write paths (create, update, delete) MUST call
invalidate_resume_list_cache() to keep the cache fresh.

The 1-hour TTL is a safety net — invalidation is the primary freshness
mechanism. If invalidation is ever missed, the cache self-heals within
1 hour rather than serving stale data indefinitely.
"""

from django.core.cache import cache

# 1 hour — primary freshness via invalidation; TTL is the safety net
RESUME_LIST_CACHE_TTL = 60 * 60


def resume_list_cache_key(user) -> str:
    """Build cache key for a user's resume list.

    Accepts a User instance or any object with .pk. Using pk (UUID)
    rather than email keeps the key stable across email changes.
    """
    return f"resume_list:{user.pk}"


def invalidate_resume_list_cache(user) -> None:
    """Delete the resume list cache entry for a user.

    Called from every write path (create, save, delete) on the Resume
    model. Idempotent — safe to call when no cache entry exists.
    """
    cache.delete(resume_list_cache_key(user))
