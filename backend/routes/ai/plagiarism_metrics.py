"""Pure functions for computing deterministic plagiarism/progression metrics.

No DB, no HTTP. Unit-testable in isolation.
"""

import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import List, Tuple

# Strips `# ...` comments but only after a non-escape character. Simple heuristic;
# avoids the overhead of a full Python parser. Good enough for structural compare.
_COMMENT_RE = re.compile(r"#.*$", re.MULTILINE)
_BLANK_LINE_RE = re.compile(r"\n\s*\n", re.MULTILINE)

MAX_SUBMISSION_CHARS = 8000


def _normalize_code(code: str) -> str:
    """Strip comments, trailing whitespace, collapse blank lines, normalize whitespace.

    Used for structural similarity so that cosmetic reformatting (whitespace,
    comments) doesn't inflate the apparent edit size.
    """
    stripped = _COMMENT_RE.sub("", code)
    stripped = stripped.replace("\r\n", "\n").replace("\t", "    ")
    # Strip trailing whitespace from each line (handles leftover space before
    # a stripped comment, and also ignores random end-of-line spaces).
    stripped = "\n".join(line.rstrip() for line in stripped.split("\n"))
    stripped = _BLANK_LINE_RE.sub("\n", stripped)
    return stripped.strip()


def compute_submission_metrics(code: str) -> dict:
    """Per-submission stats."""
    normalized = _normalize_code(code)
    return {
        "total_chars": len(code),
        "normalized_chars": len(normalized),
        "line_count": code.count("\n") + 1 if code else 0,
    }


def _to_utc(ts: datetime) -> datetime:
    """Convert to UTC; treat naive datetimes as UTC rather than raising."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def compute_pairwise_metrics(
    prev_code: str,
    prev_ts: datetime,
    new_code: str,
    new_ts: datetime,
) -> dict:
    """Deltas between two consecutive submissions.

    Returns a dict suitable for PairwiseMetrics(**result).
    """
    raw_matcher = SequenceMatcher(None, prev_code, new_code, autojunk=False)
    norm_matcher = SequenceMatcher(
        None,
        _normalize_code(prev_code),
        _normalize_code(new_code),
        autojunk=False,
    )

    ops = raw_matcher.get_opcodes()
    chars_added = sum(
        j2 - j1 for tag, _, _, j1, j2 in ops if tag in ("insert", "replace")
    )
    chars_removed = sum(
        i2 - i1 for tag, i1, i2, _, _ in ops if tag in ("delete", "replace")
    )

    elapsed_sec = max(0.0, (_to_utc(new_ts) - _to_utc(prev_ts)).total_seconds())

    if elapsed_sec > 0:
        chars_added_per_minute: float | None = round(chars_added / (elapsed_sec / 60), 2)
    else:
        chars_added_per_minute = None

    return {
        "elapsed_seconds": round(elapsed_sec, 1),
        "chars_added": chars_added,
        "chars_removed": chars_removed,
        "chars_added_per_minute": chars_added_per_minute,
        "raw_similarity": round(raw_matcher.ratio(), 4),
        "normalized_similarity": round(norm_matcher.ratio(), 4),
    }


def select_submissions_for_analysis(
    submissions: List, max_count: int = 10
) -> Tuple[List, bool]:
    """Sample submissions to stay under max_count.

    Keeps the first and last submissions (so progression arc endpoints are
    always visible) plus evenly-spaced interior samples. Returns
    (sampled_subs, was_sampled).
    """
    if len(submissions) <= max_count:
        return list(submissions), False
    n = len(submissions)
    step = (n - 1) / (max_count - 1)
    # Use a set to deduplicate in case of rounding collisions, then sort.
    indices = sorted({round(i * step) for i in range(max_count)})
    # Guarantee first and last are present even if rounding drops one.
    if 0 not in indices:
        indices = [0] + indices
    if (n - 1) not in indices:
        indices.append(n - 1)
    indices = sorted(set(indices))
    return [submissions[i] for i in indices], True


def truncate_code(code: str, max_chars: int = MAX_SUBMISSION_CHARS) -> Tuple[str, bool]:
    """Truncate a single submission's code to max_chars with a clear marker.

    Returns (possibly_truncated_code, was_truncated).
    """
    if len(code) <= max_chars:
        return code, False
    omitted = len(code) - max_chars
    truncated = (
        code[:max_chars] + f"\n# ... truncated, {omitted} chars omitted ...\n"
    )
    return truncated, True
