"""Parity contract between the Celery exercise worker and the browser harness.

The in-browser runner (frontend/src/pyodide/exercise_harness.py) is an
extraction of backend/exercise_worker/tasks.py: same check semantics, same
row shapes, same normalized envelope. Students must get identical results
whether their code runs in Pyodide or falls back to the worker, and stored
submissions from either path must satisfy the same frontend contract. These
tests exec the exact file the browser ships under CPython and compare it
against the worker on shared fixtures — any semantic drift fails here before
it reaches students.

The harness file reaches the test container through a dedicated read-only
volume in docker-compose.yml (the test-runner otherwise mounts only
backend/ and tutorial_data/).
"""

import importlib.util
import json
from pathlib import Path

import pytest

from backend.exercise_worker import tasks as worker

HARNESS_PATH = (
    Path(__file__).resolve().parents[3]
    / "frontend"
    / "src"
    / "pyodide"
    / "exercise_harness.py"
)


def _load_harness():
    spec = importlib.util.spec_from_file_location(
        "exercise_harness", HARNESS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = _load_harness()


def _normalize_traceback(traceback_text):
    """The comparable part of a traceback: the frames inside the student's
    exec'd code plus the final exception line. Frames pointing into
    tasks.py vs exercise_harness.py legitimately differ."""
    if traceback_text is None:
        return None
    lines = traceback_text.rstrip("\n").split("\n")
    kept = [line for line in lines if '"<string>"' in line]
    kept.append(lines[-1])
    return kept


def _run_both(code, entry_function, test_code):
    """Run one fixture through the worker and the harness; return comparable
    envelopes plus the raw pair for extra assertions."""
    worker_result = worker.run_exercise(code, entry_function, test_code)
    harness_result = json.loads(
        harness.run_exercise_json(code, entry_function, test_code)
    )

    for result in (worker_result, harness_result):
        assert set(result) == {
            "status",
            "message",
            "passed",
            "test_results",
            "duration_ms",
            "traceback",
            "stdout",
        }
        if result["duration_ms"] is not None:
            assert isinstance(result["duration_ms"], float)

    def comparable(result):
        out = dict(result)
        out.pop("duration_ms")
        out["traceback"] = _normalize_traceback(out["traceback"])
        return out

    assert comparable(worker_result) == comparable(harness_result)
    return worker_result, harness_result


ADD_CODE = "def add(a, b):\n    return a + b"

ADD_TEST_CODE = (
    "def test_add():\n"
    '    """adds two numbers"""\n'
    "    check(add(1, 2), 3)\n"
)


def test_passing_submission():
    result, _ = _run_both(ADD_CODE, "add", ADD_TEST_CODE)
    assert result["status"] == "success"
    assert result["passed"] is True
    (case,) = result["test_results"]
    assert case["name"] == "adds two numbers"
    assert case["actual"] == "3"
    assert case["expected"] == 3


def test_failing_check_rows_jsonable_expected_repr_actual():
    test_code = (
        "def test_add():\n"
        "    check(add('a', 'b'), ('a', 'b'), name='tuple expected')\n"
    )
    result, _ = _run_both(ADD_CODE, "add", test_code)
    assert result["status"] == "success"
    assert result["passed"] is False
    (case,) = result["test_results"]
    # expected goes through a JSON round-trip (tuple -> list), actual is repr
    assert case["expected"] == ["a", "b"]
    assert case["actual"] == "'ab'"


def test_unjsonable_expected_falls_back_to_repr():
    test_code = "def test_add():\n    check(add(1, 2), {3})\n"
    result, _ = _run_both(ADD_CODE, "add", test_code)
    (case,) = result["test_results"]
    assert case["expected"] == "{3}"


def test_check_output_stores_raw_text_and_tolerates_whitespace():
    code = "def greet():\n    print('hi  ')\n    print('there')"
    test_code = (
        "def test_greet():\n"
        "    with capture() as out:\n"
        "        greet()\n"
        "    check_output(out.text, 'hi\\nthere\\n')\n"
    )
    result, _ = _run_both(code, "greet", test_code)
    assert result["passed"] is True
    (case,) = result["test_results"]
    assert case["actual"] == "hi  \nthere\n"
    assert case["expected"] == "hi\nthere\n"


def test_missing_entry_function():
    result, _ = _run_both("def other():\n    return 1", "add", ADD_TEST_CODE)
    assert result["status"] == "error"
    assert "must define a function named 'add'" in result["message"]


def test_crash_before_tests_keeps_partial_stdout_and_traceback():
    result, _ = _run_both(
        "print('before')\nraise ValueError('bad module')",
        "add",
        ADD_TEST_CODE,
    )
    assert result["status"] == "error"
    assert "failed to run before any tests started" in result["message"]
    assert "bad module" in result["traceback"]
    assert result["stdout"] == "before\n"


def test_no_tests_is_an_authoring_error():
    result, _ = _run_both(ADD_CODE, "add", None)
    assert result["status"] == "error"
    assert "defines no tests" in result["message"]


def test_broken_test_script_is_an_authoring_error():
    result, _ = _run_both(ADD_CODE, "add", "this is not python")
    assert result["status"] == "error"
    assert "test script failed to run" in result["message"]


def test_exception_in_one_test_fails_that_row_only():
    test_code = (
        "def test_boom():\n"
        '    """explodes"""\n'
        "    raise RuntimeError('boom')\n"
        "def test_ok():\n"
        "    check(add(1, 2), 3)\n"
    )
    result, _ = _run_both(ADD_CODE, "add", test_code)
    assert result["status"] == "success"
    assert result["passed"] is False
    by_name = {row["name"]: row for row in result["test_results"]}
    assert by_name["explodes"]["error"] == "RuntimeError: boom"
    assert by_name["test_ok"]["passed"] is True


def test_student_defined_test_function_is_not_collected():
    code = ADD_CODE + "\ndef test_fake():\n    check(1, 1)\n"
    result, _ = _run_both(code, "add", ADD_TEST_CODE)
    # only the script's own test ran: one row, from test_add
    assert [row["name"] for row in result["test_results"]] == [
        "adds two numbers"
    ]


def test_top_level_exercise_uses_module_output():
    code = "total = 2 + 3\nprint('total is', total)"
    test_code = (
        "def test_output():\n"
        "    check_output(module_output, 'total is 5')\n"
        "def test_var():\n"
        "    check(total, 5)\n"
    )
    result, _ = _run_both(code, "", test_code)
    assert result["status"] == "success"
    assert result["passed"] is True


def test_stdout_only_present_when_nonblank_and_bounded():
    result, _ = _run_both(
        f"print('x' * {worker.MAX_STDOUT_CHARS * 2})\n{ADD_CODE}",
        "add",
        ADD_TEST_CODE,
    )
    assert len(result["stdout"]) == worker.MAX_STDOUT_CHARS

    quiet, _ = _run_both(ADD_CODE, "add", ADD_TEST_CODE)
    assert quiet["stdout"] is None


def test_capture_text_is_bounded():
    code = (
        "def shout():\n"
        f"    print('y' * {worker.MAX_STDOUT_CHARS * 2})"
    )
    test_code = (
        "def test_shout():\n"
        "    with capture() as out:\n"
        "        shout()\n"
        f"    check(len(out.text), {worker.MAX_STDOUT_CHARS})\n"
    )
    result, _ = _run_both(code, "shout", test_code)
    assert result["passed"] is True


def test_harness_has_no_celery_dependency():
    """The harness must stay stdlib-only (Pyodide ships no wheels), and the
    file must actually be present — a missing docker-compose volume mount
    should fail loudly here, not skip."""
    assert HARNESS_PATH.exists(), (
        "exercise_harness.py not found — is the ./frontend/src/pyodide "
        "volume mounted in docker-compose.yml?"
    )
    source = HARNESS_PATH.read_text()
    assert "import celery" not in source
    assert "from celery" not in source
