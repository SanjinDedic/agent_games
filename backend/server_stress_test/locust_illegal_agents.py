"""
Fixed-rate benchmark: steady drip of ILLEGAL agents under a legal load.

Each illegal agent type -- spin (infinite loop), security (AST-rejected),
runtime error -- submits at ILLEGAL_PER_MIN (default 5/min), while legal valid
agents submit at LEGAL_PER_MIN (default 50/min). Intended duration: 3 minutes.
Slow-but-legal agents are deliberately absent: they validate successfully, so
they belong to the legal mix, and this test keeps the legal load a clean
baseline signal.

Unlike locust_greedy_pig.py (weighted max-throughput), rates here are absolute:
every user class has a fixed user count and constant_throughput pacing, so the
offered load stays at the target regardless of how slow the server responds
(pacing can only *cap* the rate -- if latency exceeds the per-user interval the
actual rate falls below target; the summary shows what was achieved).

Run with -u equal to the total fixed users (default 5+2+1+1 = 9):

    BENCHMARK_TOKEN=<secret> \
    locust -f backend/server_stress_test/locust_illegal_agents.py \
        --headless -u 9 -r 9 -t 3m \
        --host https://your-prod-host \
        --csv bench_illegal

Failures on the spin/security/runtime rows are EXPECTED (those agents must be
rejected); read submit_valid for clean latency. Pair with monitor_cpu.sh --
the whole point of a steady illegal drip is to catch a validator that leaks
runaway processes over time.
"""

import logging
import os

from locust import HttpUser, constant_throughput, events, task

from bench_common import (
    CPU_CHECK_FOOTER,
    apply_benchmark_headers,
    install_summary,
    runtime_error_code,
    security_code,
    spin_code,
    submit,
    valid_code,
)

# Target rates, per minute.
LEGAL_PER_MIN = float(os.environ.get("LEGAL_PER_MIN", "50"))
ILLEGAL_PER_MIN = float(os.environ.get("ILLEGAL_PER_MIN", "5"))

# Users per class. Each class's rate is split across its users, so a user's
# submit interval is users/rate minutes -- keep that comfortably above the
# expected latency or the achieved rate drops below target. Spin agents block
# for the full ~5-8s validator timeout, hence 2 users (24s interval each)
# instead of 1 (12s), for headroom under backpressure.
VALID_USERS = int(os.environ.get("VALID_USERS", "5"))
SPIN_USERS = int(os.environ.get("SPIN_USERS", "2"))
SECURITY_USERS = int(os.environ.get("SECURITY_USERS", "1"))
RUNTIME_USERS = int(os.environ.get("RUNTIME_USERS", "1"))

TOTAL_USERS = VALID_USERS + SPIN_USERS + SECURITY_USERS + RUNTIME_USERS


class _BenchUser(HttpUser):
    abstract = True

    def on_start(self):
        apply_benchmark_headers(self)


class ValidUser(_BenchUser):
    fixed_count = VALID_USERS
    wait_time = constant_throughput(LEGAL_PER_MIN / 60 / VALID_USERS)

    @task
    def submit_valid(self):
        submit(self, valid_code(), "submit_valid", expect_success=True)


class SpinUser(_BenchUser):
    fixed_count = SPIN_USERS
    wait_time = constant_throughput(ILLEGAL_PER_MIN / 60 / SPIN_USERS)

    @task
    def submit_spin(self):
        submit(self, spin_code(), "submit_spin", expect_success=False)


class SecurityUser(_BenchUser):
    fixed_count = SECURITY_USERS
    wait_time = constant_throughput(ILLEGAL_PER_MIN / 60 / SECURITY_USERS)

    @task
    def submit_security(self):
        submit(self, security_code(), "submit_security", expect_success=False)


class RuntimeErrorUser(_BenchUser):
    fixed_count = RUNTIME_USERS
    wait_time = constant_throughput(ILLEGAL_PER_MIN / 60 / RUNTIME_USERS)

    @task
    def submit_runtime_error(self):
        submit(self, runtime_error_code(), "submit_runtime_error", expect_success=False)


@events.init.add_listener
def _check_user_count(environment, **kwargs):
    opts = environment.parsed_options
    if opts is not None and opts.num_users != TOTAL_USERS:
        logging.warning(
            "-u %s does not match the %s fixed users this test defines "
            "(VALID_USERS+SPIN_USERS+SECURITY_USERS+RUNTIME_USERS); "
            "run with -u %s or the target rates will be off.",
            opts.num_users,
            TOTAL_USERS,
            TOTAL_USERS,
        )


install_summary(
    events,
    rows=[
        ("submit_valid", "valid"),
        ("submit_spin", "spin (timeout)"),
        ("submit_security", "security reject"),
        ("submit_runtime_error", "runtime error"),
    ],
    footer=CPU_CHECK_FOOTER,
)
