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

# ---------------------------------------------------------------------------
# Unearned-claim blocklists
# ---------------------------------------------------------------------------
# These lists define claim patterns that are either always forbidden
# (P&L-class) or only forbidden when absent from the veteran's source
# text (skills, credentials). Each entry is a tuple of lowercase
# trigger phrases; matching is substring-based with word-boundary
# awareness where appropriate.

# P&L phrases — always flagged when present in output. The source
# "including" a P&L phrase is rare and usually indicates the veteran
# already conflated budget/contract management with P&L. The flag
# surfaces the question to the user regardless; if they genuinely
# had P&L authority, they verify the flag and keep it.
_PNL_PHRASES = (
    "p&l",
    "pnl ",
    "p and l ",
    "profit and loss",
    "profit-and-loss",
    "profit & loss",
)

# Skill/tool phrases — flagged when present in output AND NOT present
# in source. This is the core "unearned skill" check: Claude pulls a
# JD-distinctive technical term into output to match the JD; validator
# catches it when the source doesn't back the claim.
_UNEARNED_SKILL_PATTERNS = (
    "ai/ml",
    "ai-enabled",
    "machine learning",
    "deep learning",
    "data pipeline",
    "data pipelines",
    "etl",
    "data engineering",
    "cloud infrastructure",
    "cloud-native",
    "aws",
    "azure",
    "gcp",
    "google cloud",
    "python",
    "javascript",
    "typescript",
    "kubernetes",
    "docker",
    "devops",
    "mlops",
    "saas platform",
    "enterprise software integration",
    "api integration",
    "ci/cd",
    "agile",
    "scrum",
    "kanban",
    "jira",
    "asana",
    "monday.com",
    "confluence",
)

# Credential/clearance/certification phrases — flagged when present in
# output AND NOT present in source. Recruiters verify these; fabricated
# credentials are high-harm for the veteran.
_UNEARNED_CREDENTIAL_PATTERNS = (
    "ts/sci",
    "top secret",
    "top-secret",
    "secret clearance",
    "sci clearance",
    "pmp",
    "pmp certified",
    "pmp-certified",
    "series 7",
    "series 65",
    "series 66",
    "series 63",
    "cfa",
    "cpa",
    "cissp",
    "aws certified",
    "aws-certified",
    "certified scrum master",
    "csm",
    "itil",
    "six sigma",
    "lean six sigma",
    "green belt",
    "black belt",
    "mba",
    "phd",
    "jd",
    "md",
)

# Dollar-amount aggregate pattern. If output contains a dollar amount
# that does NOT appear verbatim in the source, it is flagged. This
# covers summed totals ('$1.4M+', '$1.7M portfolio') and any other
# numeric fabrication the numeric-pattern check might otherwise miss.
# Pattern matches $N, $N.N, $NK, $NM, $NB, with optional + suffix.
_DOLLAR_AMOUNT_PATTERN = re.compile(
    r"\$\s?\d+(?:[.,]\d+)?\s?[KMB]?\+?",
    re.IGNORECASE,
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

    # Check 3 — unearned-claim checks (P&L, skills, credentials, aggregates)
    flags.extend(flag_unearned_claims(bullet, source_text))

    return flags


def flag_unearned_claims(text: str, source_text: str) -> list[str]:
    """
    Scan `text` (a bullet or the summary) for unearned-claim patterns
    that the prompt-layer hard limits cannot reliably enforce.

    Flags four categories:
      1. P&L-class phrases — always flagged when present in output,
         regardless of source.
      2. Skill/tool claims — flagged when present in output but not
         present in source_text.
      3. Credential claims — flagged when present in output but not
         present in source_text.
      4. Dollar-amount aggregates — flagged when a dollar amount in
         output does not appear verbatim in source_text.

    Returns a list of human-readable flag messages. Empty list means
    no unearned claims detected.
    """
    flags: list[str] = []
    if not text:
        return flags

    text_lower = text.lower()
    source_lower = (source_text or "").lower()

    # Category 1: P&L phrases — always flagged
    for phrase in _PNL_PHRASES:
        if phrase in text_lower:
            flags.append(
                f"P&L claim detected ('{phrase.strip()}'). Verify you had "
                f"profit-and-loss accountability — COR roles, budget "
                f"management, and program oversight do not establish P&L "
                f"authority. If this was budget or contract work, rephrase "
                f"as 'managed budget', 'program financials', or 'financial "
                f"stewardship'."
            )
            break  # one P&L flag per text is enough

    # Category 2: Unearned skill/tool claims
    for phrase in _UNEARNED_SKILL_PATTERNS:
        if phrase in text_lower and phrase not in source_lower:
            flags.append(
                f"Skill/tool claim '{phrase}' appears in output but is not "
                f"present in your source resume. Verify you have this "
                f"experience; if not, remove or rephrase."
            )

    # Category 3: Unearned credentials
    for phrase in _UNEARNED_CREDENTIAL_PATTERNS:
        if phrase in text_lower and phrase not in source_lower:
            flags.append(
                f"Credential '{phrase.upper() if len(phrase) <= 6 else phrase}' "
                f"appears in output but is not present in your source resume. "
                f"Recruiters verify credentials — fabricating them is "
                f"career-harming. Remove if you do not hold this credential."
            )

    # Category 4: Dollar-amount aggregates and fabrications
    output_amounts = _DOLLAR_AMOUNT_PATTERN.findall(text)
    for amount in output_amounts:
        # Normalize: strip whitespace and trailing + (a hedge modifier, not a
        # distinct amount) before comparing against source.
        normalized = re.sub(r"\s+", "", amount).rstrip("+").lower()
        source_normalized = re.sub(r"\s+", "", source_text or "").lower()
        if normalized not in source_normalized:
            flags.append(
                f"Dollar amount '{amount}' in output does not match any "
                f"verbatim figure in your source resume. Verify this is not "
                f"a summed total across separate source figures; each source "
                f"dollar amount should appear only in the bullet where it "
                f"originated."
            )

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
