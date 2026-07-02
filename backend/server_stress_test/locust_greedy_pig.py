"""
Greedy Pig submission load benchmark.

Drives the gated /diagnostics/benchmark-submit endpoint, which runs the real
validator load path (1 game + N simulations of greedy_pig) while skipping
rate-limiting and DB logging. No teams.json, no login -- a single shared secret
header authorizes every request, so you can push 100s of submissions/min.

The endpoint is disabled unless the API process has BENCHMARK_TOKEN set in its
environment; pass the same value here via BENCHMARK_TOKEN.

By default the load is a realistic *mix*: mostly valid agents, plus a small
fraction of problematic ones (infinite loop, slow-but-legal, security-rejected,
runtime error). The problematic agents exist to exercise the validator's
reject / timeout / kill paths under load -- the paths that, when broken, leave a
worker spinning a core at 100%. Pair this run with monitor_cpu.sh: after the
load stops the validator CPU should fall back to idle. If it stays hot, a killed
agent leaked a runaway process. See README.md.

Run headless (example: ramp to 50 concurrent users, 1/s spawn, 2 min):

    BENCHMARK_TOKEN=<secret> \
    locust -f backend/server_stress_test/locust_greedy_pig.py \
        --headless -u 50 -r 1 -t 2m \
        --host https://your-prod-host \
        --csv bench

Read the per-agent-type rows of the summary (submit_valid, submit_spin, ...);
"submit_valid" is the clean throughput/latency number. submit_spin requests are
*meant* to fail (the validator times them out), so their failures are expected
and counted separately -- don't read them as capacity loss.
"""

import logging
import os
import random

from locust import HttpUser, between, events, task

BENCHMARK_TOKEN = os.environ.get("BENCHMARK_TOKEN", "")

# How long each simulated user pauses between submissions. Set WAIT_MIN=WAIT_MAX=0
# (the default) to push maximum throughput; raise them to model realistic users.
WAIT_MIN = float(os.environ.get("WAIT_MIN", "0"))
WAIT_MAX = float(os.environ.get("WAIT_MAX", "0"))

# Simulations per submission. 20 matches what /user/submit-agent sends in prod.
NUM_SIMULATIONS = int(os.environ.get("NUM_SIMULATIONS", "20"))

# Mix of agent types, as locust task weights (relative, not percentages). Tune
# any of them via env. Defaults keep valid agents dominant and the expensive
# spin agents rare -- each spin agent holds a validator child slot for the full
# ~5s timeout, so even a few of them throttle everything behind the semaphore.
# Set W_SPIN=0 to benchmark pure valid throughput (the old behaviour).
W_VALID = int(os.environ.get("W_VALID", "80"))
W_SPIN = int(os.environ.get("W_SPIN", "3"))
W_SLOW = int(os.environ.get("W_SLOW", "7"))
W_SECURITY = int(os.environ.get("W_SECURITY", "5"))
W_RUNTIME = int(os.environ.get("W_RUNTIME", "5"))


# --- Agent code generators --------------------------------------------------
# Each returns a distinct payload per call (random tweak) so no layer can cache
# a result -- every request does real work.

VALID_TEMPLATE = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        if banked + unbanked >= {win_target}:
            return "bank"
        if game_state["roll_no"] >= {roll_cap}:
            return "bank"
        if unbanked > {threshold}:
            return "bank"
        return "continue"
"""


def valid_code():
    """A valid, slightly-randomized threshold strategy. Always validates and
    runs to completion -- this is the clean throughput baseline."""
    return VALID_TEMPLATE.format(
        win_target=random.choice([90, 100, 110, 120]),
        roll_cap=random.choice([4, 5, 6, 7]),
        threshold=random.randint(10, 28),
    )


# Infinite loop in make_decision: never returns, so the validator must hit its
# hard timeout and terminate() the child. THIS is the agent that catches a spin
# regression -- if terminate() doesn't fully reap the worker, a core stays at
# 100% after the run. The trailing nonce keeps each payload unique.
SPIN_TEMPLATE = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        while True:
            pass  # nonce {nonce}
        return "bank"
"""


def spin_code():
    return SPIN_TEMPLATE.format(nonce=random.randint(0, 10**9))


# Heavy but *legal*: burns CPU in a finite loop that finishes under the 5s cap,
# so it validates successfully while stressing the worker pool (and exposing the
# busy worker to docker stats) without tripping the timeout. Tune the iteration
# count via the literal below if the validator host is much faster/slower.
SLOW_TEMPLATE = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        total = 0
        for i in range({iters}):
            total += (i * i) % 7
        if total % 2 == 0:
            return "bank"
        return "continue"
"""


def slow_code():
    # ~hundreds of k iterations per decision; many decisions per game x sims.
    return SLOW_TEMPLATE.format(iters=random.choice([200000, 300000, 400000]))


# Security violation: rejected by the AST check in the parent before any fork.
# Exercises the cheap reject path -- should be near-instant and never spin.
SECURITY_TEMPLATES = [
    """
from games.greedy_pig.player import Player
import os  # nonce {nonce}

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "continue"
""",
    """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return eval("'bank'")  # nonce {nonce}
""",
]


def security_code():
    return random.choice(SECURITY_TEMPLATES).format(nonce=random.randint(0, 10**9))


# Runtime fault: divides by zero on construction, so add_player raises and the
# child returns an error fast. Exercises the worker error path (not a timeout).
RUNTIME_TEMPLATE = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        self.ratio = {numerator} / 0

    def make_decision(self, game_state):
        return "bank"
"""


def runtime_error_code():
    return RUNTIME_TEMPLATE.format(numerator=random.randint(1, 1000))


class BenchmarkUser(HttpUser):
    wait_time = between(WAIT_MIN, WAIT_MAX)

    def on_start(self):
        if not BENCHMARK_TOKEN:
            print(
                "WARNING: BENCHMARK_TOKEN not set -- every request will 403. "
                "Export the same secret the API process was started with."
            )
        self.client.headers.update({"X-Benchmark-Token": BENCHMARK_TOKEN})

    def _submit(self, code: str, name: str, expect_success: bool):
        """POST one submission and record it under its own stat name.

        expect_success controls what counts as a pass: valid/slow agents must
        come back status=success; spin/security/runtime agents are *supposed* to
        be rejected, so for them an "error" status is the correct outcome and a
        "success" is the bug (a bad agent slipped through)."""
        payload = {
            "code": code,
            "game_name": "greedy_pig",
            "num_simulations": NUM_SIMULATIONS,
        }
        with self.client.post(
            "/diagnostics/benchmark-submit",
            json=payload,
            name=name,
            catch_response=True,
        ) as response:
            # The endpoint returns HTTP 200 with a status field even on logical
            # errors (disabled gate, bad token, validator error), so inspect the
            # body rather than trusting the status code.
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}: {response.text[:200]}")
                return
            try:
                body = response.json()
            except ValueError:
                response.failure(f"non-JSON response: {response.text[:200]}")
                return
            status = body.get("status")
            if expect_success:
                if status == "success":
                    response.success()
                else:
                    response.failure(body.get("message", "unknown error"))
            else:
                # A bad agent that the validator *rejected* is the desired path.
                if status == "success":
                    response.failure(
                        f"bad agent unexpectedly validated: {body.get('message')}"
                    )
                else:
                    response.success()

    @task(W_VALID)
    def submit_valid(self):
        self._submit(valid_code(), "submit_valid", expect_success=True)

    @task(W_SPIN)
    def submit_spin(self):
        self._submit(spin_code(), "submit_spin", expect_success=False)

    @task(W_SLOW)
    def submit_slow(self):
        self._submit(slow_code(), "submit_slow", expect_success=True)

    @task(W_SECURITY)
    def submit_security(self):
        self._submit(security_code(), "submit_security", expect_success=False)

    @task(W_RUNTIME)
    def submit_runtime_error(self):
        self._submit(runtime_error_code(), "submit_runtime_error", expect_success=False)


@events.init.add_listener
def _quiet_periodic_tables(environment, **kwargs):
    """Silence locust's repeating per-interval stats tables (and the auto
    end-of-run table). They use a dedicated logger with its own handler that
    locust configures in setup_logging *after* this file is imported, so we
    must raise its level here (on the init event), not at module load. We print
    one clean summary block instead (see _print_summary)."""
    logging.getLogger("locust.stats_logger").setLevel(logging.ERROR)


@events.quitting.add_listener
def _print_summary(environment, **kwargs):
    """One clean block at shutdown. Run with `--loglevel WARNING` to silence
    locust's repeating per-interval tables and leave only this."""
    stats = environment.stats

    def _fmt(entry, label):
        if entry is None or entry.num_requests == 0:
            return f"  {label:<22}:  (none)"
        pct = entry.get_response_time_percentile
        return (
            f"  {label:<22}: {entry.num_requests:>6} req  "
            f"{entry.num_failures:>5} fail  "
            f"avg {entry.avg_response_time:>6.0f} ms  "
            f"p95 {pct(0.95):>6.0f} ms  "
            f"max {entry.max_response_time:>6.0f} ms"
        )

    s = stats.total
    duration = (s.last_request_timestamp or 0) - (s.start_time or 0)
    rps = s.num_requests / duration if duration > 0 else 0
    line = "=" * 78
    # Per-agent-type breakdown, in a stable order.
    names = [
        ("submit_valid", "valid"),
        ("submit_slow", "slow (legal)"),
        ("submit_spin", "spin (timeout)"),
        ("submit_security", "security reject"),
        ("submit_runtime_error", "runtime error"),
    ]
    rows = []
    for name, label in names:
        # entries is keyed by (name, method); missing -> _fmt prints "(none)".
        entry = stats.entries.get((name, "POST"))
        rows.append(_fmt(entry, label))
    body = "\n".join(rows)
    print(
        f"\n{line}\n BENCHMARK RESULT\n{line}\n"
        f" total requests : {s.num_requests}\n"
        f" total failures : {s.num_failures}\n"
        f" throughput     : {rps * 60:,.0f} submissions/min  ({rps:.1f} req/s)\n"
        f" avg latency    : {s.avg_response_time:.0f} ms  (all types blended)\n"
        f"{'-' * 78}\n by agent type (failures on spin/security/runtime are EXPECTED):\n"
        f"{body}\n"
        f"{line}\n"
        f" CPU check: run monitor_cpu.sh alongside this. After the load ends the\n"
        f" validator container CPU should drop back to idle. If it stays hot, a\n"
        f" timed-out agent leaked a runaway process (a core stuck at 100%).\n"
        f"{line}"
    )
