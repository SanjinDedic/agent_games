"""Unit tests for plagiarism metrics (pure functions)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from backend.routes.ai.plagiarism_metrics import (
    CPS_LIKELY_THRESHOLD,
    CPS_PROBABLE_THRESHOLD,
    MAX_SUBMISSION_CHARS,
    _normalize_code,
    classify_typing_speed,
    compute_complexity_jump,
    compute_pairwise_metrics,
    compute_submission_metrics,
    compute_template_similarity,
    count_ast_constructs,
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


# --- classify_typing_speed (deterministic threshold) ---


def test_classify_speed_none_is_normal():
    assert classify_typing_speed(None) == "normal"


def test_classify_speed_zero_is_normal():
    assert classify_typing_speed(0.0) == "normal"


def test_classify_speed_below_probable_threshold_is_normal():
    assert classify_typing_speed(3.9) == "normal"
    assert classify_typing_speed(CPS_PROBABLE_THRESHOLD) == "normal"  # exactly 4 → normal


def test_classify_speed_above_probable_is_probable():
    assert classify_typing_speed(4.1) == "probable_plagiarism"
    assert classify_typing_speed(5.999) == "probable_plagiarism"
    assert classify_typing_speed(CPS_LIKELY_THRESHOLD) == "probable_plagiarism"  # exactly 6 → probable


def test_classify_speed_above_likely_is_likely():
    assert classify_typing_speed(6.01) == "likely_plagiarism"
    assert classify_typing_speed(100.0) == "likely_plagiarism"


# --- compute_pairwise_metrics deterministic flag integration ---


def test_pairwise_flag_normal_below_threshold():
    # 60 chars in 60 seconds = 1 char/sec → normal
    pm = compute_pairwise_metrics("", T0, "x" * 60, T0 + timedelta(seconds=60))
    assert pm["chars_added_per_second"] == 1.0
    assert pm["deterministic_flag"] == "normal"


def test_pairwise_flag_probable_between_4_and_6():
    # 500 chars in 100 seconds = 5 chars/sec → probable
    pm = compute_pairwise_metrics("", T0, "x" * 500, T0 + timedelta(seconds=100))
    assert pm["chars_added_per_second"] == 5.0
    assert pm["deterministic_flag"] == "probable_plagiarism"


def test_pairwise_flag_likely_above_6():
    # 1000 chars in 100 seconds = 10 chars/sec → likely
    pm = compute_pairwise_metrics("", T0, "x" * 1000, T0 + timedelta(seconds=100))
    assert pm["chars_added_per_second"] == 10.0
    assert pm["deterministic_flag"] == "likely_plagiarism"


def test_pairwise_cps_none_when_elapsed_zero():
    pm = compute_pairwise_metrics("a", T0, "abcdefghij", T0)
    assert pm["chars_added_per_second"] is None
    assert pm["deterministic_flag"] == "normal"


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


# --- compute_template_similarity ---


def test_template_similarity_identical():
    tpl = "def foo():\n    return 1\n"
    assert compute_template_similarity(tpl, tpl) == 1.0


def test_template_similarity_completely_different():
    tpl = "def foo():\n    return 1\n"
    code = "class Banana:\n    def peel(self, x, y, z):\n        return x * y + z\n"
    sim = compute_template_similarity(code, tpl)
    assert sim < 0.5


def test_template_similarity_cosmetic_changes_still_high():
    tpl = "def foo():\n    return 1\n"
    code = "def foo():  # modified\n    return 1  # same logic\n"
    sim = compute_template_similarity(code, tpl)
    assert sim == 1.0  # comments stripped + trailing whitespace stripped


def test_template_similarity_empty_template_returns_zero():
    assert compute_template_similarity("anything", "") == 0.0


# --- count_ast_constructs ---


def test_ast_constructs_simple_class():
    code = "class Foo:\n    def bar(self):\n        pass\n"
    counts = count_ast_constructs(code)
    assert counts["ClassDef"] == 1
    assert counts["FunctionDef"] == 1
    assert counts["structural_total"] == 2
    assert counts["total"] >= 2


def test_ast_constructs_with_comprehension_and_import():
    code = "import os\nfrom sys import path\nx = [i for i in range(10)]\n"
    counts = count_ast_constructs(code)
    assert counts["Import"] == 1
    assert counts["ImportFrom"] == 1
    assert counts["ListComp"] == 1
    assert counts["structural_total"] == 3


def test_ast_constructs_counts_logic_nodes():
    """If/For/While/Compare are now counted as logic constructs."""
    code = "def foo(x):\n    if x > 5:\n        for i in range(x):\n            pass\n"
    counts = count_ast_constructs(code)
    assert counts["FunctionDef"] == 1
    assert counts.get("If", 0) >= 1
    assert counts.get("For", 0) >= 1
    assert counts.get("Compare", 0) >= 1
    assert counts["logic_total"] >= 3
    assert counts["total"] == counts["structural_total"] + counts["logic_total"]


def test_ast_constructs_with_try_except():
    code = "try:\n    pass\nexcept:\n    pass\n"
    counts = count_ast_constructs(code)
    assert counts.get("Try", 0) >= 1
    assert counts["total"] >= 1


def test_ast_constructs_syntax_error_returns_zero():
    code = "def foo( broken"
    counts = count_ast_constructs(code)
    assert counts["total"] == 0
    assert counts["structural_total"] == 0
    assert counts["logic_total"] == 0


def test_ast_constructs_empty_code():
    counts = count_ast_constructs("")
    assert counts["total"] == 0


def test_ast_constructs_with_decorators():
    code = "@staticmethod\ndef foo():\n    pass\n"
    counts = count_ast_constructs(code)
    assert counts.get("Decorator", 0) == 1
    assert counts.get("FunctionDef", 0) == 1


def test_ast_greedy_pig_progression_detected():
    """Two greedy pig submissions that differ only in logic should show a delta."""
    simple = (
        "from games.greedy_pig.player import Player\n"
        "import random\n\n"
        "class CustomPlayer(Player):\n"
        "    def make_decision(self, game_state):\n"
        "        return random.choice(['continue', 'bank'])\n"
    )
    complex_code = (
        "from games.greedy_pig.player import Player\n"
        "import random\n\n"
        "class CustomPlayer(Player):\n"
        "    def make_decision(self, game_state):\n"
        "        my_unbanked = game_state['unbanked_money'][self.name]\n"
        "        if my_unbanked > 20:\n"
        "            return 'bank'\n"
        "        elif my_unbanked > 10 and self.my_rank(game_state) <= 2:\n"
        "            return 'bank'\n"
        "        return 'continue'\n"
    )
    simple_counts = count_ast_constructs(simple)
    complex_counts = count_ast_constructs(complex_code)
    assert complex_counts["total"] > simple_counts["total"]
    assert complex_counts["logic_total"] > simple_counts["logic_total"]


# --- compute_complexity_jump ---


def test_complexity_jump_normal():
    prev = {"total": 6, "structural_total": 3, "logic_total": 3, "FunctionDef": 2, "ClassDef": 1, "If": 2, "Compare": 1}
    new = {"total": 8, "structural_total": 3, "logic_total": 5, "FunctionDef": 2, "ClassDef": 1, "If": 3, "Compare": 2}
    result = compute_complexity_jump(prev, new)
    assert result["complexity_jump_flag"] == "normal"
    assert result["constructs_added"] == 2


def test_complexity_jump_suspicious_many_new_types():
    prev = {"total": 4, "structural_total": 4, "logic_total": 0, "FunctionDef": 2, "ClassDef": 1, "Import": 1}
    new = {"total": 14, "structural_total": 5, "logic_total": 9,
           "FunctionDef": 2, "ClassDef": 1, "Import": 1, "ListComp": 1,
           "If": 3, "For": 2, "Compare": 3, "BoolOp": 1}
    result = compute_complexity_jump(prev, new)
    # 10 constructs added, 5 new types → suspicious or highly_suspicious
    assert result["complexity_jump_flag"] in ("suspicious", "highly_suspicious")
    assert len(result["new_construct_types"]) >= 4


def test_complexity_jump_highly_suspicious_triple():
    prev = {"total": 5, "structural_total": 3, "logic_total": 2}
    new = {"total": 16, "structural_total": 6, "logic_total": 10}
    result = compute_complexity_jump(prev, new)
    assert result["complexity_jump_flag"] == "highly_suspicious"


def test_complexity_jump_highly_suspicious_from_low_to_high():
    prev = {"total": 4, "structural_total": 4, "logic_total": 0}
    new = {"total": 15, "structural_total": 5, "logic_total": 10}
    result = compute_complexity_jump(prev, new)
    assert result["complexity_jump_flag"] == "highly_suspicious"


def test_complexity_jump_decrease_is_normal():
    prev = {"total": 15, "structural_total": 5, "logic_total": 10}
    new = {"total": 6, "structural_total": 3, "logic_total": 3}
    result = compute_complexity_jump(prev, new)
    assert result["complexity_jump_flag"] == "normal"
    assert result["constructs_added"] == 0


