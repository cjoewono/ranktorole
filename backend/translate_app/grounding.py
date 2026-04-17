"""
Metric grounding validator for military-to-civilian bullet translation.

Scans LLM-generated bullets for numeric claims (money, percentages, counts,
durations) and flags any that do not appear in the source military text.

Pure-Python. No LLM. No network. Deterministic.
"""
import re


# Matches: $2M, $2.1M, 35%, 40+, 12-person, 18 months, 99.8%, 2.4M, 40+
# Captures the raw match so we can normalise and search for it.
_NUMERIC_PATTERN = re.compile(
    r"""
    (?<![A-Za-z])                          # not preceded by a letter
    (?:\$)?                                # optional $
    \d{1,3}(?:,\d{3})*(?:\.\d+)?           # digits with optional commas/decimal
    (?:\s?[KMB])?                          # optional K/M/B suffix
    \s?(?:%|\+|-\s?(?:person|people|member|soldier|troops?))?  # optional unit
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Scope-inflation markers. Not exhaustive — this is a conservative first pass.
# We flag the bullet only if the verb appears in the output but NOT in the source.
_SCOPE_VERBS = (
    "led", "directed", "commanded", "oversaw", "headed",
    "spearheaded", "orchestrated", "championed", "drove",
)


def _normalise_number(raw: str) -> str:
    """Strip whitespace, commas, and dollar signs for loose matching."""
    return raw.replace(",", "").replace("$", "").replace(" ", "").lower().strip()


def _number_appears_in_source(raw_number: str, source_lower: str) -> bool:
    """
    Return True if a numeric claim from a bullet plausibly appears in source.

    We normalise both sides and check containment. This is intentionally loose:
    we want to flag clearly-fabricated numbers, not trip on formatting differences.
    """
    normalised = _normalise_number(raw_number)
    if not normalised or normalised in {"%", "+", "-"}:
        return True  # lone punctuation — nothing to validate

    # Strip trailing unit markers for the containment check
    bare = re.sub(r"[^\d.]", "", normalised)
    if not bare:
        return True

    # Check both the full normalised form and the bare digits
    source_normalised = source_lower.replace(",", "").replace("$", "")
    return normalised in source_normalised or bare in source_normalised


def flag_bullet(bullet: str, source_text: str) -> list[str]:
    """
    Scan one bullet against the source military text. Return a list of
    human-readable flag strings for any ungrounded claims found.

    Empty list means no issues detected.
    """
    if not bullet or not source_text:
        return []

    source_lower = source_text.lower()
    flags: list[str] = []

    # Check 1 — ungrounded numeric claims
    for match in _NUMERIC_PATTERN.findall(bullet):
        raw = match.strip()
        if not raw or raw in {"%", "+", "-"}:
            continue
        # Skip bare single digits that are almost certainly ordinals or list markers
        bare = re.sub(r"[^\d.]", "", raw)
        if bare and len(bare) == 1 and not any(c in raw for c in "$%+K M B"):
            continue
        if not _number_appears_in_source(raw, source_lower):
            flags.append(f"Unverified metric: '{raw}' — confirm against your records")

    # Check 2 — scope-inflation verbs not present in source
    bullet_lower = bullet.lower()
    for verb in _SCOPE_VERBS:
        pattern = rf"\b{verb}\b"
        if re.search(pattern, bullet_lower) and not re.search(pattern, source_lower):
            flags.append(
                f"Scope check: '{verb}' — verify this matches your actual role"
            )
            break  # one scope flag per bullet is enough

    return flags


def flag_translation(roles: list[dict], source_text: str) -> list[dict]:
    """
    Run flag_bullet against every bullet in every role. Returns a parallel
    structure listing flags per bullet.

    Input:
        roles: list of {title, org, dates, bullets: list[str]}
        source_text: the raw military experience text the bullets derive from

    Returns:
        list of {role_index: int, bullet_index: int, flags: list[str]}
        — only entries with at least one flag are included
    """
    results: list[dict] = []
    for role_idx, role in enumerate(roles or []):
        for bullet_idx, bullet in enumerate(role.get("bullets") or []):
            flags = flag_bullet(bullet, source_text)
            if flags:
                results.append({
                    "role_index": role_idx,
                    "bullet_index": bullet_idx,
                    "flags": flags,
                })
    return results


def flag_summary(summary: str, source_text: str) -> list[str]:
    """
    Run flag_bullet against the summary text. Returns a flat list of flag
    strings. Empty list means the summary passed grounding checks.

    Summary-specific concern: aggregate fabrications. The prompt forbids them,
    but the validator catches any numeric claim that doesn't trace to source —
    which includes aggregates (since '$1.2M total' won't appear in source if
    the source lists individual amounts).
    """
    if not summary or not source_text:
        return []
    return flag_bullet(summary, source_text)
