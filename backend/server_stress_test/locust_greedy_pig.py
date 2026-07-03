"""
Greedy Pig submission load benchmark (weighted mix).

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

For fixed-rate scenarios instead of weighted max-throughput, see
locust_illegal_agents.py (illegal agents at a steady drip) and
locust_legal_only.py (pure valid at a target req/s).

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

import os

from locust import HttpUser, between, events, task

from bench_common import (
    CPU_CHECK_FOOTER,
    apply_benchmark_headers,
    install_summary,
    runtime_error_code,
    security_code,
    slow_code,
    spin_code,
    submit,
    valid_code,
)

# How long each simulated user pauses between submissions. Set WAIT_MIN=WAIT_MAX=0
# (the default) to push maximum throughput; raise them to model realistic users.
WAIT_MIN = float(os.environ.get("WAIT_MIN", "0"))
WAIT_MAX = float(os.environ.get("WAIT_MAX", "0"))

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


class BenchmarkUser(HttpUser):
    wait_time = between(WAIT_MIN, WAIT_MAX)

    def on_start(self):
        apply_benchmark_headers(self)

    @task(W_VALID)
    def submit_valid(self):
        submit(self, valid_code(), "submit_valid", expect_success=True)

    @task(W_SPIN)
    def submit_spin(self):
        submit(self, spin_code(), "submit_spin", expect_success=False)

    @task(W_SLOW)
    def submit_slow(self):
        submit(self, slow_code(), "submit_slow", expect_success=True)

    @task(W_SECURITY)
    def submit_security(self):
        submit(self, security_code(), "submit_security", expect_success=False)

    @task(W_RUNTIME)
    def submit_runtime_error(self):
        submit(self, runtime_error_code(), "submit_runtime_error", expect_success=False)


install_summary(
    events,
    rows=[
        ("submit_valid", "valid"),
        ("submit_slow", "slow (legal)"),
        ("submit_spin", "spin (timeout)"),
        ("submit_security", "security reject"),
        ("submit_runtime_error", "runtime error"),
    ],
    footer=CPU_CHECK_FOOTER,
)
