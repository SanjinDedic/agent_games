"""
Shared pieces for the *exercises* benchmark: the exercise-code generators, the
admin-login and run-exercise POST helpers.

This is the exercises analogue of bench_common.py (submissions). It is not a
locustfile -- run locust_exercises.py in this directory instead.

Why a different endpoint than the submission benchmark
------------------------------------------------------
Submissions have a dedicated gated benchmark endpoint (/diagnostics/
benchmark-submit) that skips the rate limit and the DB write. Exercises already
have an endpoint with exactly those properties: POST /tutorial/admin/run-exercise
is the admin editor's stateless "dry run" -- it drives the real path

    API -> enqueue on the `exercises` queue -> worker-exercises (the slim
    sandbox: no secrets/DB/S3, ~96MB RAM, 0.5s soft / 1.5s hard time limit,
    fresh process per task) -> await result

with NO DB write and NO rate limit. So instead of adding a second gated
endpoint, this benchmark just logs in as admin once (on_start) and hammers
run-exercise. Unlike agent submissions, exercises have NO AST safety gate --
the container is the sandbox -- which is why the timeout/kill path (ex_timeout
below) is the most important one to exercise under load.
"""

import os
import random

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

# How hard the "slow but legal" exercise works. The heavy loop must finish
# inside the worker's 0.5s soft limit or it becomes a timeout (a false ex_slow
# failure). Lower these if the worker host is slow / heavily loaded; raise them
# to put more CPU pressure on the two worker-exercises slots.
SLOW_ITERS = (int(os.environ.get("SLOW_ITERS_MIN", "200000")),
              int(os.environ.get("SLOW_ITERS_MAX", "400000")))


# --- Exercise generators ----------------------------------------------------
# Each returns a (code, entry_function, test_code) triple -- exactly the body
# /tutorial/admin/run-exercise expects. A per-call nonce keeps every payload
# unique so nothing can be cached. entry_function is always "solve".
#
# The test scripts use the three helpers the worker injects into the student
# namespace: check(actual, expected), check_output(text, expected), capture().


def valid_exercise():
    """Correct code that passes its checks -> status success, passed True.
    The clean throughput/latency baseline."""
    k = random.randint(1, 1000)
    code = f"def solve(n):\n    return n + {k}  # nonce {random.randint(0, 10**9)}\n"
    test = (
        "def test_add():\n"
        f"    check(solve(0), {k})\n"
        f"    check(solve(7), {k + 7})\n"
    )
    return code, "solve", test


def wrong_exercise():
    """Code that runs fine but returns the wrong answer -> status success,
    passed False. This is the single most common real outcome (a student's
    attempt is simply incorrect); the worker must handle it as a clean run,
    not an error. Exercises the full success path with failing checks."""
    k = random.randint(1, 1000)
    code = f"def solve(n):\n    return n + {k}  # nonce {random.randint(0, 10**9)}\n"
    # Expected values deliberately don't match what solve returns.
    test = (
        "def test_add():\n"
        f"    check(solve(0), {k + 1})\n"
        f"    check(solve(3), {k + 100})\n"
    )
    return code, "solve", test


def slow_exercise():
    """Heavy but *legal* finite loop that finishes under the 0.5s soft limit ->
    status success. Puts real CPU pressure on the two worker-exercises slots
    without tripping the timeout. Tune SLOW_ITERS_MIN/MAX if the host is much
    faster/slower."""
    iters = random.randint(*SLOW_ITERS)
    code = (
        "def solve(n):\n"
        "    total = 0\n"
        f"    for i in range({iters}):\n"
        "        total += (i * i) % 7\n"
        f"    return total + n  # nonce {random.randint(0, 10**9)}\n"
    )
    # Check only that it returns an int, so the value doesn't have to be
    # recomputed here -- the point is the CPU burn, not the answer.
    test = (
        "def test_type():\n"
        "    check(isinstance(solve(1), int), True)\n"
        "    check(isinstance(solve(2), int), True)\n"
    )
    return code, "solve", test


def timeout_exercise():
    """Infinite loop -> the worker's 0.5s soft limit fires, and because a bare
    `while True: pass` doesn't swallow it, the run ends in a timeout error
    (SIGKILL backstop at 1.5s if it had). status error.

    THIS is the leak hunter: if the hard kill fails to reap the child, a core
    stays pegged at 100% after the load stops. Pair the run with
    `MATCH=worker-exercises ./monitor_cpu.sh`. A status of "success" here would
    mean the spinner was never killed -- the bug."""
    code = (
        "def solve(n):\n"
        "    while True:\n"
        f"        pass  # nonce {random.randint(0, 10**9)}\n"
        "    return n\n"
    )
    test = "def test_x():\n    check(solve(1), 1)\n"
    return code, "solve", test


def error_exercise():
    """Module-level error: the code raises while being exec'd, before any test
    runs -> status error ("Your code failed to run before any tests started").
    Exercises the fast error path (no fork work wasted)."""
    code = (
        f"x = {random.randint(1, 1000)} / 0  # nonce {random.randint(0, 10**9)}\n"
        "def solve(n):\n"
        "    return n\n"
    )
    test = "def test_x():\n    check(solve(1), 1)\n"
    return code, "solve", test


# --- Request helpers ---------------------------------------------------------


def admin_login(user):
    """Call from on_start: log in as admin and attach the Bearer token to every
    later request. run-exercise is admin-only, so without this every call 401s."""
    with user.client.post(
        "/auth/admin-login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        name="admin-login",
        catch_response=True,
    ) as r:
        if r.status_code != 200:
            r.failure(f"admin login failed: HTTP {r.status_code} {r.text[:200]}")
            print(
                f"WARNING: admin login failed ({r.status_code}). Every "
                "run-exercise will 401. Check ADMIN_USERNAME/ADMIN_PASSWORD "
                "and that --host points at a stack whose admin password matches."
            )
            return
        try:
            token = r.json().get("access_token")
        except ValueError:
            r.failure(f"admin login: non-JSON response {r.text[:200]}")
            return
        if not token:
            r.failure("admin login returned no access_token")
            return
        user.client.headers.update({"Authorization": f"Bearer {token}"})
        r.success()


def run_exercise(user, triple, name, expect, require_passed=None):
    """POST one exercise run and record it under its own stat name.

    `expect` is the status the worker should return: "success" (the run
    produced test results) or "error" (the run never got that far -- a timeout
    or an exec failure). For ex_timeout/ex_error, "error" is the *correct*
    outcome and a "success" is the bug, so those failures are expected and
    counted separately. `require_passed`, when set, additionally asserts the
    passed flag (True for valid, False for wrong)."""
    code, entry_function, test_code = triple
    payload = {"code": code, "entry_function": entry_function, "test_code": test_code}
    with user.client.post(
        "/tutorial/admin/run-exercise",
        json=payload,
        name=name,
        catch_response=True,
    ) as response:
        if response.status_code != 200:
            response.failure(f"HTTP {response.status_code}: {response.text[:200]}")
            return
        try:
            body = response.json()
        except ValueError:
            response.failure(f"non-JSON response: {response.text[:200]}")
            return
        status = body.get("status")
        if status not in ("success", "error"):
            response.failure(f"unexpected status {status!r}: {body.get('message')}")
            return
        if status != expect:
            response.failure(
                f"expected status {expect!r}, got {status!r}: {body.get('message')}"
            )
            return
        if require_passed is not None and bool(body.get("passed")) != require_passed:
            response.failure(
                f"expected passed={require_passed}, got passed={body.get('passed')}"
            )
            return
        response.success()


# --- Summary footer ----------------------------------------------------------

EX_CPU_FOOTER = (
    " CPU/leak check: run  MATCH=worker-exercises ./monitor_cpu.sh  alongside\n"
    " this (local stack only). After the load ends the worker-exercises CPU\n"
    " should fall back to idle. If it stays hot, a timed-out (ex_timeout)\n"
    " exercise leaked a runaway process the 1.5s hard SIGKILL failed to reap.\n"
)
