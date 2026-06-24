"""
Greedy Pig submission load benchmark.

Drives the gated /diagnostics/benchmark-submit endpoint, which runs the real
validator load path (1 game + N simulations of greedy_pig) while skipping
rate-limiting and DB logging. No teams.json, no login -- a single shared secret
header authorizes every request, so you can push 100s of submissions/min.

The endpoint is disabled unless the API process has BENCHMARK_TOKEN set in its
environment; pass the same value here via BENCHMARK_TOKEN.

Run headless (example: ramp to 50 concurrent users, 1/s spawn, 2 min):

    BENCHMARK_TOKEN=<secret> \
    locust -f backend/server_stress_test/locust_greedy_pig.py \
        --headless -u 50 -r 1 -t 2m \
        --host https://your-prod-host \
        --csv bench

Read the result off the "submit_agent" row of the summary:
    Requests = total submissions, "/s" * 60 = submissions per minute (X),
    "Average (ms)" = average latency (Y).
"""

import os
import random

from locust import HttpUser, between, task

BENCHMARK_TOKEN = os.environ.get("BENCHMARK_TOKEN", "")

# How long each simulated user pauses between submissions. Set WAIT_MIN=WAIT_MAX=0
# (the default) to push maximum throughput; raise them to model realistic users.
WAIT_MIN = float(os.environ.get("WAIT_MIN", "0"))
WAIT_MAX = float(os.environ.get("WAIT_MAX", "0"))

# Simulations per submission. 20 matches what /user/submit-agent sends in prod.
NUM_SIMULATIONS = int(os.environ.get("NUM_SIMULATIONS", "20"))

CODE_TEMPLATE = """
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


def random_greedy_pig_code():
    """A valid, slightly-randomized threshold strategy so each submission is a
    distinct payload (defeats any caching) but always validates and runs."""
    return CODE_TEMPLATE.format(
        win_target=random.choice([90, 100, 110, 120]),
        roll_cap=random.choice([4, 5, 6, 7]),
        threshold=random.randint(10, 28),
    )


class BenchmarkUser(HttpUser):
    wait_time = between(WAIT_MIN, WAIT_MAX)

    def on_start(self):
        if not BENCHMARK_TOKEN:
            print(
                "WARNING: BENCHMARK_TOKEN not set -- every request will 403. "
                "Export the same secret the API process was started with."
            )
        self.client.headers.update({"X-Benchmark-Token": BENCHMARK_TOKEN})

    @task
    def submit_agent(self):
        payload = {
            "code": random_greedy_pig_code(),
            "game_name": "greedy_pig",
            "num_simulations": NUM_SIMULATIONS,
        }
        with self.client.post(
            "/diagnostics/benchmark-submit",
            json=payload,
            name="submit_agent",
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
            if body.get("status") == "success":
                response.success()
            else:
                response.failure(body.get("message", "unknown error"))
