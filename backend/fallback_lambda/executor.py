"""Execution core for the exercise/snippet server fallback — celery-free.

Ported near line-for-line from the retired backend/exercise_worker/tasks.py
(the slim Celery worker's whole codebase) so the parity test keeps pinning
these semantics against the browser-shipped Pyodide harness
(frontend/src/pyodide/exercise_harness.py). Everything here must stay
stdlib-only: this module ships inside the Lambda zip and also runs in the
local subprocess fallback, neither of which installs dependencies.

Exercises run with ZERO code validation: unlike agent submissions, there is
no AST safety gate, so arbitrary student code executes here. The Lambda (or
the scrubbed-env local subprocess) is the sandbox — no secrets, no DB or S3
connection — and ``run_exercise_isolated``/``run_snippet_isolated`` give
every run a fresh forked child process, so one submission cannot contaminate
the next even on a warm Lambda container.

Time limits reproduce the old Celery pair exactly:

- soft 0.5s — SIGALRM in the child raises :class:`ExecutionTimeout` at the
  current instruction, which maps to the timeout envelope. Like Celery's
  SoftTimeLimitExceeded it is an ``Exception`` subclass on purpose: student
  code with a bare ``except Exception`` swallows it, and only the hard kill
  reliably reaps a spinner.
- hard 1.5s — the parent SIGKILLs the child's whole process group
  (``setsid`` + ``killpg``, so fork-bomb descendants die too) and returns
  the same timeout envelope.

An exercise's tests are an admin-trusted Python test script exec'd into the
same namespace as the student's code, so test functions call student
functions by name. The script defines ``test_*`` functions and uses three
injected helpers:

- check(actual, expected, name=None) — append one pass/fail result row
- check_output(text, expected, name=None) — whitespace-tolerant text compare
- capture() — context manager capturing stdout, exposing ``.text``

An empty ``entry_function`` means a top-level-code exercise: no function is
required, and tests grade module-level state directly — variables by bare
name, print output via the injected ``module_output`` string (everything the
student's code printed while it was exec'd, truncated at MAX_STDOUT_CHARS).
The student's own source is injected alongside it as ``module_source``, so a
test can grade *how* an answer was reached (e.g. that the expected value was
worked out rather than typed in as a literal). Both names are injected on
every run, so both are reserved in the student namespace.

A failing check is a normal outcome ("status": "success", test not passed) —
"status": "error" means the code never got as far as producing test results
(syntax error, missing function, timeout).
"""

import contextlib
import io
import json
import multiprocessing
import os
import signal
import time
import traceback as tb
from typing import Any, Dict, List, Optional


class ExecutionTimeout(Exception):
    """Soft-limit signal, stand-in for Celery's SoftTimeLimitExceeded.

    Deliberately an ``Exception`` subclass for exact behavioral parity with
    the old worker: student code that catches ``Exception`` swallows it and
    spins on until the hard kill, same as before.
    """


# An exercise run is a handful of pure-function calls — 0.5s of CPU is
# generous. Plain constants, not env-overridable: nothing needs to shorten
# 0.5s further for tests, and a constant cannot drift between the API client
# and the deployed Lambda.
EXERCISE_TIMEOUT_SECONDS = 0.5

# Hard SIGKILL backstop, 1s past the soft limit: student code with a bare
# `except Exception` swallows ExecutionTimeout, and only the hard kill
# reliably reaps a spinner.
EXERCISE_TIME_LIMIT = EXERCISE_TIMEOUT_SECONDS + 1

EXERCISE_TIMEOUT_MESSAGE = (
    f"Your code consumes too much time - the tests did not finish within "
    f"{EXERCISE_TIMEOUT_SECONDS} seconds. It may be stuck in a loop."
)

SNIPPET_TIMEOUT_MESSAGE = (
    f"Your code did not finish within {EXERCISE_TIMEOUT_SECONDS} seconds. "
    f"It may be stuck in a loop."
)

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

    Round-trips through JSON so a row looks the same whether the run happened
    in-process (unit tests) or crossed the Lambda/pipe boundary (a tuple
    `expected` is a list either way); a value JSON can't encode at all (a
    set, an object) falls back to its repr instead of crashing the run.
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
    normally; an error dict (the "status": "error" shape) only when the
    script itself fails to exec — an authoring bug, not a student failure.
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
    except ExecutionTimeout:
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
        except ExecutionTimeout:
            # Same rule as the exec above: the budget covers the whole run —
            # swallowing this would defer the kill to the hard limit.
            raise
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
            exec(code, namespace)  # noqa: S102 - isolated child process
    except ExecutionTimeout:
        raise
    except Exception:
        return {
            "status": "error",
            "message": "Your code failed to run before any tests started.",
            "traceback": tb.format_exc(),
        }
    finally:
        # Re-emit into the run-level stdout panel so students still see what
        # they printed, including partial output before a crash or timeout.
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
    namespace["module_source"] = code

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
    """Execute the student's code and run the exercise's test script on it.

    Direct call = no time limit (unit tests, parity test). Production paths
    go through :func:`run_exercise_isolated`, which forks and arms the soft
    timer before calling this.
    """
    buf = io.StringIO()
    result: Dict[str, Any]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = _execute_tests(code, entry_function, test_code)
    except ExecutionTimeout:
        # Only reached when the student's code didn't swallow it; a bare
        # `except Exception` in their code spins on until the hard-kill
        # deadline, which the parent maps to the same message.
        result = {
            "status": "error",
            "message": EXERCISE_TIMEOUT_MESSAGE,
        }
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

    Unlike an exercise run there is no entry function and no test script —
    the captured stdout (or the traceback) IS the result. ``__name__`` is
    ``"__main__"`` so demo code behind a main guard runs.
    """
    buf = io.StringIO()
    result: Dict[str, Any]
    t0 = time.perf_counter()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(code, {"__name__": "__main__"})  # noqa: S102 - sandboxed child
        result = {
            "status": "success",
            "duration_ms": (time.perf_counter() - t0) * 1000,
        }
    except ExecutionTimeout:
        result = {
            "status": "error",
            "message": SNIPPET_TIMEOUT_MESSAGE,
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


# ---------------------------------------------------------------------------
# Process isolation — the replacement for Celery's prefork time limits.
# ---------------------------------------------------------------------------

# Grace on top of the hard deadline: fork + module import in the child eat
# into wall time before the soft timer is armed.
_HARD_KILL_GRACE = 0.2

# Fork, not spawn: instant child start (spawn re-imports the interpreter,
# dwarfing the 0.5s budget) and the only start method the soft-timer
# arithmetic assumes. Works on Lambda and in the Linux containers; macOS
# defaults to spawn, so be explicit.
_mp = multiprocessing.get_context("fork")


def _soft_limit_handler(signum, frame):
    raise ExecutionTimeout()


def _child_main(conn, kind: str, payload: Dict[str, Any]) -> None:
    """Forked child: own process group, armed soft timer, one run, one send.

    ``setsid`` makes the child a process-group leader so the parent's
    ``killpg`` reaps any descendants student code forked (a plain SIGKILL on
    the child would leave fork-bomb grandchildren running).
    """
    os.setsid()
    signal.signal(signal.SIGALRM, _soft_limit_handler)
    signal.setitimer(signal.ITIMER_REAL, EXERCISE_TIMEOUT_SECONDS)
    if kind == "snippet":
        envelope = run_snippet(payload["code"])
    else:
        envelope = run_exercise(
            payload["code"], payload["entry_function"], payload.get("test_code")
        )
    signal.setitimer(signal.ITIMER_REAL, 0)
    # JSON string over the pipe: same round-trip the Celery broker applied,
    # so a tuple `expected` arrives as a list either way.
    conn.send(json.dumps(envelope))


def _kill_child(process) -> None:
    """SIGKILL the child's whole process group, then reap it."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass  # already exited (or died before setsid) — join reaps it
    process.join()


def _run_isolated(
    kind: str, payload: Dict[str, Any], timeout_envelope: Dict[str, Any]
) -> Dict[str, Any]:
    """Run one exercise/snippet in a fresh forked child under the time limits.

    A child that dies without sending a result (hard kill, OOM, crash) maps
    to the canonical timeout envelope — the same collapse the old path made
    for TimeLimitExceeded/WorkerLostError.
    """
    parent_conn, child_conn = _mp.Pipe(duplex=False)
    process = _mp.Process(target=_child_main, args=(child_conn, kind, payload))
    process.start()
    child_conn.close()
    envelope: Optional[Dict[str, Any]] = None
    try:
        if parent_conn.poll(EXERCISE_TIME_LIMIT + _HARD_KILL_GRACE):
            envelope = json.loads(parent_conn.recv())
    except (EOFError, OSError, ValueError):
        envelope = None
    finally:
        _kill_child(process)
        parent_conn.close()
    if envelope is None:
        return timeout_envelope
    return envelope


def run_exercise_isolated(
    code: str, entry_function: str, test_code: Optional[str]
) -> Dict[str, Any]:
    """`run_exercise` in a fresh child process under the 0.5s/1.5s limits."""
    return _run_isolated(
        "exercise",
        {"code": code, "entry_function": entry_function, "test_code": test_code},
        normalize_result({"status": "error", "message": EXERCISE_TIMEOUT_MESSAGE}),
    )


def run_snippet_isolated(code: str) -> Dict[str, Any]:
    """`run_snippet` in a fresh child process under the 0.5s/1.5s limits."""
    return _run_isolated(
        "snippet",
        {"code": code},
        normalize_snippet_result(
            {"status": "error", "message": SNIPPET_TIMEOUT_MESSAGE}
        ),
    )
