"""The exercises Celery app and its tasks — the slim worker's whole codebase.

The worker-exercises container image is python:alpine + celery[redis] + this
single file, imported as top-level ``tasks`` (see the Dockerfile next to it).
Everything here must therefore be stdlib+celery only — no ``backend.*``
imports, no second module. The backend image ships the same file as
``backend.exercise_worker.tasks`` so the API-side enqueue helpers
(backend/tasks/exercise_task.py) and the unit tests share one source of truth;
``backend/__init__.py`` is empty, so importing it stays as light in the fat
image as in the slim one.

Exercises run with ZERO code validation: unlike agent submissions, there is
no AST safety gate before enqueue, so arbitrary student code executes here.
The container is the sandbox — it holds no secrets, opens no DB or S3
connection, and lives under tight mem/cpu/pids limits — and
``worker_max_tasks_per_child=1`` gives every run a fresh process, so one
submission cannot contaminate the next.

An exercise's tests are an admin-trusted Python test script exec'd into the
same namespace as the student's code, so test functions call student
functions by name. The script defines ``test_*`` functions and uses three
injected helpers:

- check(actual, expected, name=None) — append one pass/fail result row
- check_output(text, expected, name=None) — whitespace-tolerant text compare
- capture() — context manager capturing stdout, exposing ``.text``

A failing check is a normal outcome ("status": "success", test not passed) —
"status": "error" means the code never got as far as producing test results
(syntax error, missing function, timeout).
"""

import contextlib
import gc
import io
import json
import os
import time
import traceback as tb
from typing import Any, Dict, List, Optional

from celery import Celery
from celery.concurrency.asynpool import AsynPool
from celery.exceptions import SoftTimeLimitExceeded
from celery.signals import worker_process_init, worker_ready

# Same 5s-stall fix as backend/tasks/celery_app.py: with max_tasks_per_child=1
# every task kills its child, and billiard only respawns children on the
# pool-maintenance tick — hardcoded to 5.0s upstream. At a 0.5s task budget a
# 5s dispatch stall dwarfs the task itself, so tick every 0.1s instead
# (maintain_pool is a cheap no-op when nothing exited).
AsynPool.timers = property(lambda self: {self.maintain_pool: 0.1})

# Same in-container/localhost switch as the backend app: inside Docker the
# broker is reachable by service name, outside by published port.
_default_broker = (
    "redis://valkey:6379/0"
    if os.path.exists("/.dockerenv")
    else "redis://localhost:6379/0"
)
broker_url = os.environ.get("CELERY_BROKER_URL", _default_broker)
result_backend = os.environ.get("CELERY_RESULT_BACKEND", broker_url)

# Named `app` so `celery -A tasks worker` finds it without a :attribute suffix.
app = Celery("exercises", broker=broker_url, backend=result_backend)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Fresh process per task: unvalidated student code can monkeypatch or leak
    # module state — the process boundary is the isolation guarantee.
    worker_max_tasks_per_child=1,
    worker_prefetch_multiplier=1,
    worker_disable_rate_limits=True,
    result_expires=300,
    broker_connection_retry_on_startup=True,
    # Early acks: a hard-killed/OOM-killed child must never cause redelivery
    # of a poisonous submission.
    task_acks_late=False,
)


# Same COW rationale as the backend app: fork-per-task means any GC pass
# dirties inherited pages. The heap here is tiny (stdlib + celery), so freeze
# it once at boot and skip GC in the one-task children.
@worker_ready.connect
def _freeze_parent_heap(**kwargs):
    gc.collect()
    gc.freeze()


@worker_process_init.connect
def _disable_gc_in_child(**kwargs):
    gc.disable()


# An exercise run is a handful of pure-function calls — 0.5s of CPU is
# generous. Plain constants, not env-overridable: nothing needs to shorten
# 0.5s further for tests, and a constant cannot drift between the enqueuing
# process and the worker. Enforcing these requires the prefork pool (`solo`
# silently ignores time limits), which is why the Dockerfile CMD does not
# pass --pool.
EXERCISE_TIMEOUT_SECONDS = 0.5

# Hard SIGKILL backstop, 1s past the soft limit: student code with a bare
# `except Exception` swallows SoftTimeLimitExceeded, and only the hard kill
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
# can't bloat the result payload through the broker.
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
    try:
        exec(code, namespace)  # noqa: S102 - isolated one-task worker process
    except SoftTimeLimitExceeded:
        raise
    except Exception:
        return {
            "status": "error",
            "message": "Your code failed to run before any tests started.",
            "traceback": tb.format_exc(),
        }

    func = namespace.get(entry_function)
    if not callable(func):
        return {
            "status": "error",
            "message": f"Your code must define a function named '{entry_function}'.",
        }

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


@app.task(
    name="exercises.run",
    soft_time_limit=EXERCISE_TIMEOUT_SECONDS,
    time_limit=EXERCISE_TIME_LIMIT,
)
def run_exercise(
    code: str, entry_function: str, test_code: Optional[str]
) -> Dict[str, Any]:
    """Execute the student's code and run the exercise's test script on it."""
    buf = io.StringIO()
    result: Dict[str, Any]
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = _execute_tests(code, entry_function, test_code)
    except SoftTimeLimitExceeded:
        # Only reached when the student's code didn't swallow it; a bare
        # `except Exception` in their code spins on until the hard time_limit
        # SIGKILL, which the router maps to the same message.
        result = {
            "status": "error",
            "message": EXERCISE_TIMEOUT_MESSAGE,
        }
    except Exception as e:  # noqa: BLE001 - the task boundary is the catch-all
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


@app.task(
    name="exercises.run_snippet",
    soft_time_limit=EXERCISE_TIMEOUT_SECONDS,
    time_limit=EXERCISE_TIME_LIMIT,
)
def run_snippet(code: str) -> Dict[str, Any]:
    """Run a lesson demo snippet: exec the code, return its output.

    Unlike ``exercises.run`` there is no entry function and no test script —
    the captured stdout (or the traceback) IS the result. Runs under the same
    sandbox guarantees: fresh process, time limits, no secrets. ``__name__``
    is ``"__main__"`` so demo code behind a main guard runs.
    """
    buf = io.StringIO()
    result: Dict[str, Any]
    t0 = time.perf_counter()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(code, {"__name__": "__main__"})  # noqa: S102 - sandboxed worker
        result = {
            "status": "success",
            "duration_ms": (time.perf_counter() - t0) * 1000,
        }
    except SoftTimeLimitExceeded:
        result = {
            "status": "error",
            "message": SNIPPET_TIMEOUT_MESSAGE,
        }
    except Exception as e:  # noqa: BLE001 - the task boundary is the catch-all
        result = {
            "status": "error",
            "message": _error_text(e),
            "traceback": tb.format_exc(),
        }
    captured = buf.getvalue()
    if captured.strip():
        result["stdout"] = captured[:MAX_STDOUT_CHARS]
    return normalize_snippet_result(result)
