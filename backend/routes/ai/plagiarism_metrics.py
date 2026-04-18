"""Pure functions for computing deterministic plagiarism/progression metrics.

No DB, no HTTP. Unit-testable in isolation.
"""

import ast
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

# Strips `# ...` comments but only after a non-escape character. Simple heuristic;
# avoids the overhead of a full Python parser. Good enough for structural compare.
_COMMENT_RE = re.compile(r"#.*$", re.MULTILINE)
_BLANK_LINE_RE = re.compile(r"\n\s*\n", re.MULTILINE)

MAX_SUBMISSION_CHARS = 8000

# Deterministic typing-speed thresholds. These are computed independently of
# any LLM call and surface as a hard heuristic signal in the PlagiarismReport.
# A fast human typist sustains ~1.5-2.5 chars/sec of raw code; anything above
# 4/sec sustained is either pasted or AI-generated.
CPS_PROBABLE_THRESHOLD = 4.0  # strictly greater → probable_plagiarism
CPS_LIKELY_THRESHOLD = 6.0    # strictly greater → likely_plagiarism


def classify_typing_speed(cps: Optional[float]) -> str:
    """Classify a chars-per-second value into a deterministic flag.

    Returns one of: "normal", "probable_plagiarism", "likely_plagiarism".
    None input (e.g. zero elapsed time) returns "normal" — we don't want to
    punish same-second edits that could just be a second save.
    """
    if cps is None:
        return "normal"
    if cps > CPS_LIKELY_THRESHOLD:
        return "likely_plagiarism"
    if cps > CPS_PROBABLE_THRESHOLD:
        return "probable_plagiarism"
    return "normal"


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
        chars_added_per_minute: Optional[float] = round(
            chars_added / (elapsed_sec / 60), 2
        )
        chars_added_per_second: Optional[float] = round(chars_added / elapsed_sec, 3)
    else:
        chars_added_per_minute = None
        chars_added_per_second = None

    deterministic_flag = classify_typing_speed(chars_added_per_second)

    return {
        "elapsed_seconds": round(elapsed_sec, 1),
        "chars_added": chars_added,
        "chars_removed": chars_removed,
        "chars_added_per_minute": chars_added_per_minute,
        "chars_added_per_second": chars_added_per_second,
        "raw_similarity": round(raw_matcher.ratio(), 4),
        "normalized_similarity": round(norm_matcher.ratio(), 4),
        "deterministic_flag": deterministic_flag,
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


# ---------------------------------------------------------------------------
# Template similarity — compare a submission to the game's starter template
# ---------------------------------------------------------------------------


def compute_template_similarity(code: str, template_code: str) -> float:
    """Normalized similarity between a submission and its game's starter template.

    Uses the normalized (comments-stripped, whitespace-collapsed) form so that
    cosmetic-only changes don't inflate the "distance from template" score.
    Returns a float in [0.0, 1.0] where 1.0 = identical to template.
    """
    if not template_code:
        return 0.0
    norm_code = _normalize_code(code)
    norm_template = _normalize_code(template_code)
    return round(
        SequenceMatcher(None, norm_template, norm_code, autojunk=False).ratio(),
        4,
    )


# ---------------------------------------------------------------------------
# AST complexity — count Python constructs to detect sophistication jumps
# ---------------------------------------------------------------------------

# Node types we count as "structural constructs" (classes, functions, imports).
_STRUCTURAL_TYPES = (
    ast.ClassDef,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Import,
    ast.ImportFrom,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.Try,
    ast.Lambda,
    ast.With,
    ast.AsyncWith,
)

# Node types that indicate logic complexity inside functions.
# These change when a student modifies decision logic even if the
# overall class/function skeleton stays the same.
_LOGIC_TYPES = (
    ast.If,
    ast.For,
    ast.While,
    ast.BoolOp,      # `and` / `or` expressions
    ast.Compare,      # comparisons like `x > 5`
    ast.IfExp,        # ternary: `a if cond else b`
    ast.Attribute,    # `self.something` / `game_state["key"]`
    ast.Subscript,    # indexing: `game_state["key"]`
)


def count_ast_constructs(code: str) -> Dict[str, int]:
    """Parse Python code and count both structural and logic constructs.

    Returns a dict with per-type counts plus "structural_total",
    "logic_total", and "total" (sum of both). If the code fails to parse,
    returns all zeros.
    """
    counts: Dict[str, int] = {}
    structural = 0
    logic = 0
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"structural_total": 0, "logic_total": 0, "total": 0}

    for node in ast.walk(tree):
        for construct_type in _STRUCTURAL_TYPES:
            if isinstance(node, construct_type):
                name = construct_type.__name__
                counts[name] = counts.get(name, 0) + 1
                structural += 1
                break
        else:
            for logic_type in _LOGIC_TYPES:
                if isinstance(node, logic_type):
                    name = logic_type.__name__
                    counts[name] = counts.get(name, 0) + 1
                    logic += 1
                    break

    # Count decorators.
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            decorator_count = len(node.decorator_list)
            if decorator_count:
                counts["Decorator"] = counts.get("Decorator", 0) + decorator_count
                structural += decorator_count

    counts["structural_total"] = structural
    counts["logic_total"] = logic
    counts["total"] = structural + logic
    return counts


def compute_complexity_jump(
    prev_constructs: Dict[str, int], new_constructs: Dict[str, int]
) -> Dict:
    """Compute the change in AST constructs between two consecutive submissions.

    Uses the combined total (structural + logic) so that adding if/for/while
    inside an existing function skeleton is still detected as a complexity jump.
    """
    prev_total = prev_constructs.get("total", 0)
    new_total = new_constructs.get("total", 0)
    constructs_added = max(0, new_total - prev_total)

    # Find construct types that are new (didn't exist in prev at all).
    new_types = []
    for key, count in new_constructs.items():
        if key in ("total", "structural_total", "logic_total"):
            continue
        if count > 0 and prev_constructs.get(key, 0) == 0:
            new_types.append(key)

    # Heuristic thresholds (now against combined total which is larger).
    if prev_total <= 4 and new_total >= 15:
        flag = "highly_suspicious"
    elif prev_total > 0 and new_total >= prev_total * 3:
        flag = "highly_suspicious"
    elif constructs_added >= 8 or len(new_types) >= 4:
        flag = "suspicious"
    else:
        flag = "normal"

    return {
        "prev_total": prev_total,
        "new_total": new_total,
        "constructs_added": constructs_added,
        "new_construct_types": sorted(new_types),
        "complexity_jump_flag": flag,
    }


