"""Runner for an exercise's optional Python test script (`Exercise.test_code`).

The script is admin-trusted (seed/admin authored, students never touch it), so
it does NOT go through validate_code — it legitimately needs things the
student allowlist forbids. It is exec'd into the same namespace as the
student's code, so test functions call student functions by name.

The script defines `test_*` functions and uses three injected helpers:

- check(actual, expected, name=None) — append one pass/fail result row
- check_output(text, expected, name=None) — whitespace-tolerant text compare
- capture() — context manager capturing stdout, exposing `.text`

Result rows have the exact shape the JSON-case loop produces
({name, call, expected, actual, passed, error}), so the frontend renders both
kinds identically.
"""

import contextlib
import io
import json
import traceback as tb
from typing import Any, Dict, List, Optional

from celery.exceptions import SoftTimeLimitExceeded

# Students print-debug; keep captured output bounded so a print inside a loop
# can't bloat the result payload through the broker. (Defined here rather than
# in exercise_task to keep the import direction one-way; exercise_task
# re-exports it.)
MAX_STDOUT_CHARS = 10_000


def _jsonable(value: Any) -> Any:
    """A value safe for Celery's JSON result serialization.

    Round-trips through JSON so a row looks the same whether the task ran
    in-process (unit tests) or through the broker (a tuple `expected` is a
    list either way); a value JSON can't encode at all (a set, an object)
    falls back to its repr instead of crashing the task result.
    """
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError):
        return repr(value)


def _normalize_output(text: str) -> str:
    """Whitespace-tolerant form: strip trailing whitespace per line and
    tolerate one trailing newline."""
    lines = [line.rstrip() for line in text.split("\n")]
    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


class _Capture:
    """Context manager wrapping redirect_stdout into a StringIO.

    Nests correctly inside the task's global capture: the innermost redirect
    wins for its block, so captured prints don't leak into the run's stdout
    panel.
    """

    def __init__(self) -> None:
        self._buf = io.StringIO()
        self._redirect = contextlib.redirect_stdout(self._buf)

    def __enter__(self) -> "_Capture":
        self._redirect.__enter__()
        return self

    def __exit__(self, *exc_info) -> bool:
        return self._redirect.__exit__(*exc_info)

    @property
    def text(self) -> str:
        return self._buf.getvalue()[:MAX_STDOUT_CHARS]


def _display_name(func) -> str:
    """A test function's user-facing name: first docstring line, else name."""
    doc = (func.__doc__ or "").strip()
    return doc.splitlines()[0] if doc else func.__name__


def _error_text(e: BaseException) -> str:
    msg = str(e)
    return f"{type(e).__name__}: {msg}" if msg else type(e).__name__


def run_test_code(
    test_code: str,
    namespace: Dict[str, Any],
    test_results: List[dict],
) -> Optional[Dict[str, Any]]:
    """Exec `test_code` into the student namespace and run its test functions.

    Appends result rows to `test_results` as checks run. Returns None
    normally; an error dict (the task's "status": "error" shape) only when
    the script itself fails to exec — an authoring bug, not a student
    failure.
    """
    # The current test's display name doubles as the default row name for
    # anonymous check()/check_output() calls inside it.
    state: Dict[str, Optional[str]] = {"current": None}

    def _append_row(name, expected, actual, passed, error=None) -> None:
        test_results.append(
            {
                "name": name or state["current"] or "check",
                "call": None,
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "error": error,
            }
        )

    def check(actual: Any, expected: Any, name: Optional[str] = None) -> bool:
        """Record one comparison row; never raises, so later checks in the
        same test still run."""
        try:
            passed = bool(actual == expected)
            error = None
        except Exception as e:  # noqa: BLE001 - a broken __eq__ fails the row
            passed = False
            error = _error_text(e)
        _append_row(name, _jsonable(expected), repr(actual), passed, error)
        return passed

    def check_output(
        text: Any, expected: str, name: Optional[str] = None
    ) -> bool:
        """Whitespace-tolerant text comparison, recorded with the raw text
        (not repr) so the UI can show real output."""
        # Accept a still-open capture() object where its .text was meant.
        if isinstance(text, _Capture):
            text = text.text
        try:
            passed = _normalize_output(text) == _normalize_output(expected)
            error = None
        except Exception as e:  # noqa: BLE001 - non-str input fails the row
            passed = False
            error = _error_text(e)
        _append_row(name, expected, text, passed, error)
        return passed

    def capture() -> _Capture:
        return _Capture()

    namespace["check"] = check
    namespace["check_output"] = check_output
    namespace["capture"] = capture

    # Snapshot before exec: only test_* callables the script itself defined
    # (or redefined) are collected, so a student defining their own test_foo
    # can neither inject rows nor shadow a real test.
    before = dict(namespace)
    try:
        exec(test_code, namespace)  # noqa: S102 - admin-trusted script
    except SoftTimeLimitExceeded:
        raise
    except Exception:
        return {
            "status": "error",
            "message": "This exercise's test script failed to run.",
            "traceback": tb.format_exc(),
        }

    tests = [
        value
        for key, value in namespace.items()
        if key.startswith("test_")
        and callable(value)
        and before.get(key) is not value
    ]

    for func in tests:
        state["current"] = _display_name(func)
        try:
            func()
        except SoftTimeLimitExceeded:
            # Same rule as the JSON case loop: the budget covers the whole
            # run — swallowing this would defer the kill to the hard limit.
            raise
        except Exception as e:  # noqa: BLE001 - a crash fails this test only
            _append_row(state["current"], None, None, False, _error_text(e))
    return None
