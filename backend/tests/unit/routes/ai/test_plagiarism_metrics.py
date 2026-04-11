"""Unit tests for plagiarism metrics (pure functions)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.routes.ai.plagiarism_metrics import (
    MAX_SUBMISSION_CHARS,
    _normalize_code,
    compute_pairwise_metrics,
    compute_submission_metrics,
    select_submissions_for_analysis,
    truncate_code,
)
from backend.routes.ai.plagiarism_prompt import SYSTEM_PROMPT


# --- compute_submission_metrics ---


def test_submission_metrics_empty():
    m = compute_submission_metrics("")
    assert m["total_chars"] == 0
    assert m["normalized_chars"] == 0
    assert m["line_count"] == 0


def test_submission_metrics_simple():
    code = "def foo():\n    return 1\n"
    m = compute_submission_metrics(code)
    assert m["total_chars"] == len(code)
    assert m["line_count"] == 3  # two \n means three lines in typical counting


# --- compute_pairwise_metrics ---


T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)
T2 = T0  # identical


def test_identical_code_similarity_one():
    code = "def foo():\n    return 1\n"
    pm = compute_pairwise_metrics(code, T0, code, T1)
    assert pm["raw_similarity"] == 1.0
    assert pm["normalized_similarity"] == 1.0
    assert pm["chars_added"] == 0
    assert pm["chars_removed"] == 0


def test_whitespace_only_diff_high_normalized_similarity():
    a = "def foo():\n    return 1\n"
    b = "def foo():\n\n\n\n    return 1\n"
    pm = compute_pairwise_metrics(a, T0, b, T1)
    # Raw has a lower similarity because extra blank lines are real chars.
    assert pm["raw_similarity"] < 1.0
    # Normalized should be (near) 1.0 because blank lines collapse.
    assert pm["normalized_similarity"] == 1.0


def test_comment_only_diff_high_normalized_similarity():
    a = "def foo():\n    return 1\n"
    b = "def foo():  # returns 1\n    return 1  # the answer\n"
    pm = compute_pairwise_metrics(a, T0, b, T1)
    # Raw similarity drops because comments add characters.
    assert pm["raw_similarity"] < 1.0
    # Normalized should be exactly 1.0 because comments are stripped.
    assert pm["normalized_similarity"] == 1.0


def test_complete_rewrite_low_similarity():
    a = "def foo():\n    return 1\n"
    b = "class Banana:\n    def peel(self, x, y, z):\n        return x * y + z\n"
    pm = compute_pairwise_metrics(a, T0, b, T1)
    assert pm["raw_similarity"] < 0.5
    assert pm["normalized_similarity"] < 0.5
    assert pm["chars_added"] > 0


def test_zero_elapsed_returns_none_cpm():
    code_a = "def foo(): pass\n"
    code_b = "def foo(): return 1\n"
    pm = compute_pairwise_metrics(code_a, T0, code_b, T2)  # same timestamp
    assert pm["elapsed_seconds"] == 0.0
    assert pm["chars_added_per_minute"] is None


def test_identical_timestamps_do_not_raise():
    # Regression: must not divide by zero.
    compute_pairwise_metrics("a", T0, "ab", T0)


def test_chars_added_per_minute_basic():
    a = ""
    b = "x" * 60  # 60 chars added
    pm = compute_pairwise_metrics(a, T0, b, T0 + timedelta(minutes=1))
    assert pm["chars_added"] == 60
    assert pm["chars_added_per_minute"] == 60.0


def test_naive_datetime_treated_as_utc():
    naive_prev = datetime(2026, 1, 1, 12, 0, 0)
    naive_new = datetime(2026, 1, 1, 12, 1, 0)
    pm = compute_pairwise_metrics("a", naive_prev, "ab", naive_new)
    assert pm["elapsed_seconds"] == 60.0


# --- truncate_code ---


def test_truncate_under_limit_unchanged():
    code = "x" * (MAX_SUBMISSION_CHARS - 1)
    result, was_truncated = truncate_code(code)
    assert was_truncated is False
    assert result == code


def test_truncate_over_limit_adds_marker():
    code = "x" * (MAX_SUBMISSION_CHARS + 500)
    result, was_truncated = truncate_code(code)
    assert was_truncated is True
    assert "truncated, 500 chars omitted" in result
    assert result.startswith("x" * MAX_SUBMISSION_CHARS)


def test_truncate_exactly_at_limit_unchanged():
    code = "x" * MAX_SUBMISSION_CHARS
    result, was_truncated = truncate_code(code)
    assert was_truncated is False
    assert result == code


# --- select_submissions_for_analysis ---


def _fake_subs(n):
    """Build n SimpleNamespace objects so we can test ordering by id."""
    return [SimpleNamespace(id=i) for i in range(n)]


def test_sampling_under_limit_keeps_all():
    subs = _fake_subs(5)
    sampled, was_sampled = select_submissions_for_analysis(subs, max_count=10)
    assert was_sampled is False
    assert len(sampled) == 5
    assert sampled == subs


def test_sampling_exactly_at_limit_keeps_all():
    subs = _fake_subs(10)
    sampled, was_sampled = select_submissions_for_analysis(subs, max_count=10)
    assert was_sampled is False
    assert len(sampled) == 10


def test_sampling_over_limit_samples_evenly_with_first_and_last():
    subs = _fake_subs(50)
    sampled, was_sampled = select_submissions_for_analysis(subs, max_count=10)
    assert was_sampled is True
    assert len(sampled) == 10
    # First and last must always be present.
    assert sampled[0].id == 0
    assert sampled[-1].id == 49


def test_sampling_preserves_order():
    subs = _fake_subs(30)
    sampled, _ = select_submissions_for_analysis(subs, max_count=10)
    ids = [s.id for s in sampled]
    assert ids == sorted(ids)


# --- SYSTEM_PROMPT contract ---


def test_system_prompt_contains_literal_json():
    # OpenAI's response_format=json_object requires the word "JSON" in the prompt.
    assert "JSON" in SYSTEM_PROMPT


def test_system_prompt_documents_required_keys():
    # Guardrails against accidentally dropping schema guidance during prompt tuning.
    for key in [
        "progression_verdict",
        "progression_reasoning",
        "ai_generation_verdict",
        "ai_generation_reasoning",
        "overall_concern_level",
        "specific_flags",
    ]:
        assert key in SYSTEM_PROMPT


# --- _normalize_code ---


def test_normalize_strips_comments_and_blank_lines():
    code = "def foo():  # comment\n\n\n    return 1  # return it\n"
    normalized = _normalize_code(code)
    assert "#" not in normalized
    # Should not contain two consecutive newlines.
    assert "\n\n" not in normalized


def test_normalize_converts_tabs_to_spaces():
    code = "def foo():\n\treturn 1\n"
    normalized = _normalize_code(code)
    assert "\t" not in normalized
