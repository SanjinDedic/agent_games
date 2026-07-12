"""Unit tests for hint_context: outcome classification, game-source loading,
and prompt rendering. Pure functions — no DB, no Celery."""

import pytest

from backend.routes.ai.hint_context import (
    HintContext,
    _render_feedback,
    _render_sim_results,
    _truncate,
    build_hint_context,
    build_hint_context_from_response,
    classify_outcome,
    load_game_source,
)


# --- classify_outcome --------------------------------------------------------


@pytest.mark.parametrize(
    "status,message,expected",
    [
        ("success", None, "success"),
        ("error", "Syntax error in code: invalid syntax (line 3)", "syntax_error"),
        ("error", "Your agent consumes too much time - validation did not finish", "timeout"),
        ("error", "Error initializing game: boom", "init_error"),
        ("error", "Failed to create player for team X: bad class", "construction_error"),
        ("error", "Error during simulation: ZeroDivisionError", "runtime_error"),
        ("error", "Agent code is not safe: unauthorized import os", "unsafe_code"),
        # The unsafe wrapper is stripped before prefix-matching, so a wrapped
        # syntax error still classifies as syntax_error.
        ("error", "Agent code is not safe: Syntax error in code: bad", "syntax_error"),
        ("error", None, "unknown_error"),
        ("error", "something novel", "unknown_error"),
    ],
)
def test_classify_outcome(status, message, expected):
    assert classify_outcome(status, message) == expected


# --- load_game_source ---------------------------------------------------------


def test_load_game_source_reads_game_package():
    source = load_game_source("greedy_pig")
    assert source is not None
    assert "# ===== backend/games/greedy_pig/greedy_pig.py =====" in source
    assert "# ===== backend/games/greedy_pig/player.py =====" in source
    # In-package test files and __init__.py are skipped.
    assert "test_threshold_calibration" not in source


@pytest.mark.parametrize(
    "name", [None, "", "no_such_game", "../greedy_pig", "greedy.pig", "a/b"]
)
def test_load_game_source_rejects_bad_names(name):
    assert load_game_source(name) is None


# --- rendering helpers ---------------------------------------------------------


def test_truncate_appends_omitted_count():
    out = _truncate("x" * 10, 6)
    assert out.startswith("xxxxxx")
    assert "[truncated 4 chars]" in out
    assert _truncate("short", 100) == "short"


def test_render_feedback_string_and_none():
    assert _render_feedback(None) is None
    assert _render_feedback("   ") is None
    assert _render_feedback(" result ") == "result"


def test_render_feedback_bare_list_is_summarised():
    assert _render_feedback([]) is None
    assert _render_feedback([1, 2, 3]) == "[3 blow-by-blow feedback entries omitted]"


def test_render_feedback_dict_drops_logs_keeps_aggregates():
    feedback = {
        "winner": "team_a",
        "rounds": [{"n": i} for i in range(50)],  # known log key
        "big": [list(range(100)) for _ in range(10)],  # oversized list
    }
    out = _render_feedback(feedback)
    assert '"winner": "team_a"' in out
    assert "[omitted blow-by-blow logs: rounds, big]" in out


def test_render_feedback_dict_with_only_logs():
    out = _render_feedback({"rounds": [1, 2, 3]})
    assert out == "[omitted blow-by-blow logs: rounds]"


def test_render_sim_results():
    assert _render_sim_results(None) is None
    assert _render_sim_results({}) is None
    # strategies/table are noise for hinting and are dropped.
    assert _render_sim_results({"strategies": {"a": "prose"}, "table": {}}) is None
    out = _render_sim_results({"total_points": {"a": 5}, "strategies": {}})
    assert "total_points" in out
    assert "strategies" not in out


# --- HintContext build + render -------------------------------------------------


def test_from_validation_response_success_renders_all_sections():
    result = {
        "status": "success",
        "message": None,
        "feedback": "You won 7 of 10 games.",
        "simulation_results": {"total_points": {"me": 42}, "strategies": {}},
        "duration_ms": 123.4,
        "stdout": "debug print\n",
    }
    ctx = HintContext.from_validation_response(
        "print('hi')", result, game_name="greedy_pig", team_name="me"
    )
    assert ctx.category == "success"
    assert ctx.sim_completed and not ctx.is_syntax_error and not ctx.is_timeout
    text = str(ctx)
    assert "Game: greedy_pig" in text
    assert "Execution time: 123.4 ms" in text
    assert "--- Captured stdout ---" in text
    assert "--- Game Feedback ---" in text
    assert "--- Simulation Results ---" in text
    assert "--- Game Source Code ---" in text
    assert "  1: print('hi')" in text


def test_from_validation_response_syntax_error_skips_game_source():
    result = {"status": "error", "message": "Syntax error in code: bad"}
    ctx = HintContext.from_validation_response(
        "def f(:", result, game_name="greedy_pig"
    )
    assert ctx.is_syntax_error
    assert ctx.game_source is None
    text = build_hint_context(ctx)
    assert "--- Validator Message ---" in text
    assert "--- Game Source Code ---" not in text


def test_from_validation_response_traceback_rendered():
    result = {
        "status": "error",
        "message": "Error during simulation: boom",
        "traceback": "Traceback (most recent call last): ...",
    }
    ctx = HintContext.from_validation_response("code", result, game_name=None)
    text = build_hint_context(ctx)
    assert "--- Stack Trace ---" in text
    assert ctx.category == "runtime_error"


def test_from_validation_response_warnings():
    # Unexpected status and an unloadable game source both surface as notes.
    ctx = HintContext.from_validation_response(
        "code", {"status": "weird"}, game_name="no_such_game"
    )
    text = build_hint_context(ctx)
    assert "--- Notes ---" in text
    assert "Unexpected validator status 'weird'" in text
    assert "Game source for 'no_such_game' could not be loaded." in text


def test_build_hint_context_from_response_one_shot():
    text = build_hint_context_from_response(
        "code",
        {"status": "success"},
        game_name="greedy_pig",
        include_game_code=False,
    )
    assert text.startswith("=== STUDENT SUBMISSION HINT CONTEXT ===")
    assert "--- Game Source Code ---" not in text
