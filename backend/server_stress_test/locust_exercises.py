"""
Tutorial *exercises* load benchmark (weighted mix).

The exercises analogue of locust_greedy_pig.py. Drives POST
/tutorial/admin/run-exercise (the admin editor's stateless dry-run), which runs
the real exercise path -- enqueue on the `exercises` queue, execute in the slim
worker-exercises sandbox (no secrets/DB/S3, ~96MB RAM, 0.5s soft / 1.5s hard
time limit, fresh process per task), await the result -- with NO DB write and
NO rate limit. It logs in as admin once (on_start) and hammers that endpoint.

The load is a realistic mix: mostly valid exercises, plus wrong-answer (still a
clean run), heavy-but-legal (CPU pressure on the two worker slots), infinite
loop (the timeout/kill path), and a module-level error (fast error path). The
ex_timeout row is the important one -- it exercises the hard-SIGKILL reap that,
if broken, leaves worker-exercises spinning a core at 100% after the load
stops. Pair the run with `MATCH=worker-exercises ./monitor_cpu.sh`.

Unlike agent submissions there is NO AST safety gate for exercises; the
container is the sandbox. So there is no "security reject" row here -- arbitrary
code just runs, which is exactly why the timeout/OOM/kill paths matter.

Run headless (example: 20 concurrent users, 2/s spawn, 1 min) against a LOCAL
stack (run-exercise needs an admin login, so point it at a stack whose admin
password you know):

    locust -f backend/server_stress_test/locust_exercises.py \
        --headless -u 20 -r 2 -t 1m \
        --host http://localhost:8000 \
        --csv bench_exercises

Read the per-type rows of the summary. "ex_valid" is the clean throughput /
latency number. ex_timeout / ex_error requests are *meant* to come back with an
error status (the worker kills / rejects them), so their "failures" are
expected and counted separately -- don't read them as capacity loss.

Env knobs: ADMIN_USERNAME/ADMIN_PASSWORD (default admin/admin), WAIT_MIN/
WAIT_MAX (per-user pause, default 0 = max throughput), the W_* mix weights
below (set any to 0 to drop that type), and SLOW_ITERS_MIN/MAX (bench_exercises).
"""

import os

from locust import HttpUser, between, events

from bench_common import install_summary
from bench_exercises import (
    EX_CPU_FOOTER,
    admin_login,
    error_exercise,
    run_exercise,
    slow_exercise,
    timeout_exercise,
    valid_exercise,
    wrong_exercise,
)

WAIT_MIN = float(os.environ.get("WAIT_MIN", "0"))
WAIT_MAX = float(os.environ.get("WAIT_MAX", "0"))

# Relative task weights (not percentages). Valid dominates; the expensive
# timeout exercises stay rare -- each holds a worker slot for the full ~0.5s
# soft limit, so even a few throttle the two-slot worker. Set any weight to 0
# to drop that type entirely.
W_VALID = int(os.environ.get("W_VALID", "80"))
W_WRONG = int(os.environ.get("W_WRONG", "8"))
W_SLOW = int(os.environ.get("W_SLOW", "4"))
W_TIMEOUT = int(os.environ.get("W_TIMEOUT", "3"))
W_ERROR = int(os.environ.get("W_ERROR", "5"))


def _valid(u):
    run_exercise(u, valid_exercise(), "ex_valid", expect="success", require_passed=True)


def _wrong(u):
    run_exercise(u, wrong_exercise(), "ex_wrong", expect="success", require_passed=False)


def _slow(u):
    run_exercise(u, slow_exercise(), "ex_slow", expect="success", require_passed=True)


def _timeout(u):
    run_exercise(u, timeout_exercise(), "ex_timeout", expect="error")


def _error(u):
    run_exercise(u, error_exercise(), "ex_error", expect="error")


_WEIGHTED = [
    (_valid, W_VALID),
    (_wrong, W_WRONG),
    (_slow, W_SLOW),
    (_timeout, W_TIMEOUT),
    (_error, W_ERROR),
]


class ExerciseUser(HttpUser):
    wait_time = between(WAIT_MIN, WAIT_MAX)
    # A weight of 0 drops that task from the mix entirely.
    tasks = {fn: w for fn, w in _WEIGHTED if w > 0}

    def on_start(self):
        admin_login(self)


install_summary(
    events,
    rows=[
        ("ex_valid", "valid (passes)"),
        ("ex_wrong", "wrong (fails checks)"),
        ("ex_slow", "slow (legal)"),
        ("ex_timeout", "timeout (killed)"),
        ("ex_error", "error (exec fails)"),
    ],
    note="failures on ex_timeout/ex_error are EXPECTED",
    unit="exercise runs",
    footer=EX_CPU_FOOTER,
)
