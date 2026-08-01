"""The in-browser exercise and snippet harness, run inside Pyodide.

Extracted from backend/fallback_lambda/executor.py — the server fallback
that in-browser execution replaces — and kept in byte-parity with it: the
check semantics, row shapes, and the normalized result envelopes (exercise
and lesson snippet alike) must be identical whether a run happens on the
server or in the browser. That contract is enforced by
backend/tests/unit/test_exercise_harness_parity.py, which execs this exact
file under CPython and compares it against the executor on shared fixtures.
If you change semantics here or in the executor, change both.

Differences from the executor, by design:

- No process isolation and no ``ExecutionTimeout`` handling — the browser's
  time limit is the main thread terminating the whole Web Worker
  (exerciseRunnerClient.js), never an in-Python exception.
- ``run_exercise_json`` / ``run_snippet_json`` are the bridge entry points:
  they JSON-serialize the envelope inside Python so only a plain ``str``
  crosses the JS bridge (no PyProxy/Map conversion issues), and the JS side
  ships it verbatim.

Must stay stdlib-only: Pyodide loads no wheels for exercises.
"""

import contextlib
import io
import json
import time
import traceback as tb
from typing import Any, Dict, List, Optional

# Students print-debug; keep captured output bounded so a print inside a loop
# can't bloat the result payload.
MAX_STDOUT_CHARS = 10_000


def normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the full ExerciseRunResponse shape consumers expect."""
    return {
        "status": result.get("status", "error"),
        "message": result.get("message"),
        "passed": result.get("passed", False),
        "test_results": result.get("test_results", []),
        "duration_ms": result.get("duration_ms"),
        "traceback": result.get("traceback"),
        "stdout": result.get("stdout"),
    }


def _jsonable(value: Any) -> Any:
    """A value safe for JSON result serialization.

    Round-trips through JSON so a row looks the same as one produced by the
    worker (a tuple `expected` is a list either way); a value JSON can't
    encode at all (a set, an object) falls back to its repr instead of
    crashing the run.
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

    Nests correctly inside the run's global capture: the innermost redirect
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
    normally; an error dict (the run's "status": "error" shape) only when
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
        except Exception as e:  # noqa: BLE001 - a crash fails this test only
            _append_row(state["current"], None, None, False, _error_text(e))
    return None


def _execute_tests(
    code: str, entry_function: str, test_code: Optional[str]
) -> Dict[str, Any]:
    """Exec the student's code, run the test script, return the raw result."""
    t0 = time.perf_counter()
    namespace: Dict[str, Any] = {"__name__": "exercise_submission"}
    module_buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(module_buf):
            exec(code, namespace)  # noqa: S102 - the browser is the sandbox
    except Exception:
        return {
            "status": "error",
            "message": "Your code failed to run before any tests started.",
            "traceback": tb.format_exc(),
        }
    finally:
        # Re-emit into the run-level stdout panel so students still see what
        # they printed, including partial output before a crash.
        print(module_buf.getvalue(), end="")

    # An empty entry_function marks a top-level-code exercise: no function
    # required, tests grade module state and ``module_output`` instead.
    if entry_function:
        func = namespace.get(entry_function)
        if not callable(func):
            return {
                "status": "error",
                "message": f"Your code must define a function named '{entry_function}'.",
            }

    namespace["module_output"] = module_buf.getvalue()[:MAX_STDOUT_CHARS]

    test_results: list = []
    if test_code:
        error = run_test_code(test_code, namespace, test_results)
        if error:
            return error

    if not test_results:
        # A missing/row-less test script would otherwise pass vacuously; this
        # is an authoring bug, not a student failure — surface it loudly.
        return {
            "status": "error",
            "message": "This exercise defines no tests.",
        }

    return {
        "status": "success",
        "passed": all(t["passed"] for t in test_results),
        "test_results": test_results,
        "duration_ms": (time.perf_counter() - t0) * 1000,
    }


def run_exercise(
    code: str, entry_function: str, test_code: Optional[str]
) -> Dict[str, Any]:
    """Execute the student's code and run the exercise's test script on it."""
    buf = io.StringIO()
    result: Dict[str, Any]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = _execute_tests(code, entry_function, test_code)
    except Exception as e:  # noqa: BLE001 - the run boundary is the catch-all
        result = {
            "status": "error",
            "message": f"Error while running tests: {str(e)}",
            "traceback": tb.format_exc(),
        }
    captured = buf.getvalue()
    if captured.strip():
        result["stdout"] = captured[:MAX_STDOUT_CHARS]
    return normalize_result(result)


def run_exercise_json(
    code: str, entry_function: str, test_code: Optional[str]
) -> str:
    """Bridge entry point: the envelope as a JSON string for the JS side."""
    return json.dumps(run_exercise(code, entry_function, test_code or None))


def normalize_snippet_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the full SnippetRunResponse shape consumers expect."""
    return {
        "status": result.get("status", "error"),
        "message": result.get("message"),
        "stdout": result.get("stdout"),
        "traceback": result.get("traceback"),
        "duration_ms": result.get("duration_ms"),
    }


def run_snippet(code: str) -> Dict[str, Any]:
    """Run a lesson demo snippet: exec the code, return its output.

    Unlike ``run_exercise`` there is no entry function and no test script —
    the captured stdout (or the traceback) IS the result. ``__name__`` is
    ``"__main__"`` so demo code behind a main guard runs.
    """
    buf = io.StringIO()
    result: Dict[str, Any]
    t0 = time.perf_counter()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(code, {"__name__": "__main__"})  # noqa: S102 - sandboxed runtime
        result = {
            "status": "success",
            "duration_ms": (time.perf_counter() - t0) * 1000,
        }
    except Exception as e:  # noqa: BLE001 - the run boundary is the catch-all
        result = {
            "status": "error",
            "message": _error_text(e),
            "traceback": tb.format_exc(),
        }
    captured = buf.getvalue()
    if captured.strip():
        result["stdout"] = captured[:MAX_STDOUT_CHARS]
    return normalize_snippet_result(result)


def run_snippet_json(code: str) -> str:
    """Bridge entry point: the envelope as a JSON string for the JS side."""
    return json.dumps(run_snippet(code))
