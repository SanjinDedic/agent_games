"""
Fixed-rate benchmark: LEGAL (valid) submissions only, at a target req/s.

Pure valid-agent throughput test -- no illegal agents, no timeout/kill paths.
Default target: 10 submissions/s for 1 minute (600/min), spread across USERS
concurrent users with constant_throughput pacing.

Each user must complete a request every USERS/TARGET_RPS seconds (default
30/10 = 3s) to hold the target; constant_throughput can only cap the rate, so
if p95 latency climbs past that interval the achieved rate falls below target.
That is itself the finding -- the server can't absorb TARGET_RPS. Raise USERS
if you want to keep offering the full rate despite slow responses.

Run with -u equal to USERS (default 30):

    BENCHMARK_TOKEN=<secret> \
    locust -f backend/server_stress_test/locust_legal_only.py \
        --headless -u 30 -r 30 -t 1m \
        --host https://your-prod-host \
        --csv bench_legal

Env knobs: TARGET_RPS (default 10), USERS (default 30, keep -u equal).
"""

import logging
import os

from locust import HttpUser, constant_throughput, events, task

from bench_common import apply_benchmark_headers, install_summary, submit, valid_code

TARGET_RPS = float(os.environ.get("TARGET_RPS", "10"))
USERS = int(os.environ.get("USERS", "30"))


class ValidOnlyUser(HttpUser):
    fixed_count = USERS
    wait_time = constant_throughput(TARGET_RPS / USERS)

    def on_start(self):
        apply_benchmark_headers(self)

    @task
    def submit_valid(self):
        submit(self, valid_code(), "submit_valid", expect_success=True)


@events.init.add_listener
def _check_user_count(environment, **kwargs):
    opts = environment.parsed_options
    if opts is not None and opts.num_users != USERS:
        logging.warning(
            "-u %s does not match USERS=%s; per-user pacing assumes %s users, "
            "so the offered rate will be %.1f req/s instead of %.1f. "
            "Run with -u %s (or set USERS to match).",
            opts.num_users,
            USERS,
            USERS,
            (TARGET_RPS / USERS) * opts.num_users,
            TARGET_RPS,
            USERS,
        )


install_summary(events, rows=[("submit_valid", "valid")])
