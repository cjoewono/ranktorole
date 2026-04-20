"""Cache key builders and TTL constants for O*NET response caching.

O*NET data (occupation titles, skills, knowledge, outlook) changes on a
quarterly-or-slower cadence. A 6-hour TTL eliminates ~95% of redundant
upstream calls without serving stale data of practical concern.

Cache keys live in Redis under the global KEY_PREFIX='rtr' set in settings,
so a key built here as 'onet_search:11b:army' is stored as
'rtr:1:onet_search:11b:army'.
"""

# 6 hours — O*NET data is effectively static within a working day
ONET_RESPONSE_CACHE_TTL = 6 * 60 * 60


def search_cache_key(keyword: str) -> str:
    """Build cache key for OnetSearchView responses."""
    return f"onet_search:{keyword.lower().strip()}"


def military_search_cache_key(keyword: str, branch: str) -> str:
    """Build cache key for OnetMilitarySearchView responses."""
    return f"onet_military:{keyword.lower().strip()}:{branch.lower().strip()}"


def career_detail_cache_key(onet_code: str) -> str:
    """Build cache key for OnetCareerDetailView responses."""
    return f"onet_career:{onet_code.lower().strip()}"
