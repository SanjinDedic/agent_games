#!/usr/bin/env python3
"""Speed benchmark: production vs local, same workload on both.

Runs one suite per environment:

  demo phase   - 2 x (launch demo -> list leagues -> join greedy_pig_demo -> submit agent)
                 submit-agent is the interesting one: AST check in the API, then a
                 validation task on a Celery worker (enqueue -> execute -> poll).
  auth phase   - admin login + institution login (bcrypt = a clean single-core CPU probe)
  institution  - 3 institution-token actions: get-all-teams (read), league-create
                 (write), team-progress (aggregate read across teams/tutorials)
  simulation   - run-simulation over greedy_pig_demo with the agents the demo phase
                 just submitted. Admin token, because the demo league belongs to the
                 Demo Institution and only admin bypasses the ownership check.

Prod timings are corrected for network latency (measured as the fastest of N /health
round-trips) so the comparison is server work vs server work, not Sydney vs your couch.

Export the PRODUCTION credentials (admin user + the "Admin Institution" institution):

    export ADMIN_PASSWORD=...
    export INSTITUTION_PASSWORD=...

Local passwords are read from the repo's committed .env - do not export those, or
the local half of the run would try prod credentials against localhost. Override
with LOCAL_ADMIN_PASSWORD / LOCAL_INSTITUTION_PASSWORD if your dev DB differs.

Usage:
    python3 .claude/skills/benchmark_prod/benchmark.py                # both envs, 3 runs
    python3 .claude/skills/benchmark_prod/benchmark.py --runs 5
    python3 .claude/skills/benchmark_prod/benchmark.py --only local   # no prod creds needed
    python3 .claude/skills/benchmark_prod/benchmark.py --json out.json

Stdlib only - no venv, no pip, runs straight off the host.
"""

import argparse
import http.client
import json
import os
import random
import ssl
import statistics
import string
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

# --- What "too slow" means -------------------------------------------------
#
# Absolute ceilings are what a *user* feels, measured as server time on prod
# (network already subtracted). Breaching one means upgrade regardless of how
# the ratio looks - a fast laptop can't excuse a slow server.
SLOW_LOGIN_MS = 1_500  # bcrypt verify; on a healthy core this is ~200-400ms
SLOW_READ_MS = 1_000  # a DB read/write round-trip
SLOW_SUBMIT_MS = 5_000  # submit-agent: students wait on this one, live
SLOW_SIM_MS = 30_000  # a full run-simulation at the configured sim count

# Relative thresholds compare prod server time against local server time.
# Calibration: a modern Apple-silicon laptop core is legitimately ~2-3x a
# mid-tier cloud vCPU, so a ratio in that band is *expected*, not a problem.
RATIO_HEALTHY = 2.5  # <= this: prod is doing fine
RATIO_WATCH = 4.0  # <= this: acceptable, keep an eye on it; above: upgrade

DEFAULT_PROD = "https://api.agentgames.io"
DEFAULT_LOCAL = "http://localhost:8000"
DEMO_LEAGUE = "greedy_pig_demo"
INSTITUTION_NAME = "Admin Institution"

# Deterministic on purpose: a random agent would make the simulation's cost
# vary run to run, and this is a stopwatch, not a tournament.
AGENT_CODE = """from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] >= 20:
            return 'bank'
        return 'continue'
"""

# Operation -> which subsystem it exercises. The verdict leans on CPU ops;
# DB ops are reported so a slow database doesn't get misread as a slow CPU.
CPU_OPS = ["admin login", "institution login", "submit agent", "run simulation", "validation exec"]
DB_OPS = ["get all teams", "create league", "team progress"]


class ApiError(RuntimeError):
    pass


def local_credentials():
    """Local passwords are NOT the prod ones you exported.

    ADMIN_PASSWORD / INSTITUTION_PASSWORD are the production secrets. Local is
    seeded by init_db from the repo's committed .env, so read them from there —
    otherwise the local half of a both-environments run tries prod credentials
    against localhost and dies on a 401. LOCAL_* overrides win if you've changed
    your dev passwords.
    """
    admin = os.environ.get("LOCAL_ADMIN_PASSWORD")
    inst = os.environ.get("LOCAL_INSTITUTION_PASSWORD")
    if admin and inst:
        return admin, inst, "LOCAL_* environment overrides"

    env_file = Path(__file__).resolve().parents[3] / ".env"
    from_file = {}
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            from_file[key.strip()] = value.strip().strip("\"'")

    # init_db's own fallbacks, for a checkout with no .env at all.
    admin = admin or from_file.get("ADMIN_PASSWORD", "admin")
    inst = inst or from_file.get("INSTITUTION_PASSWORD", "institution")
    source = f"{env_file}" if from_file else "init_db defaults"
    return admin, inst, source


class Client:
    """Keep-alive HTTP client with per-call timing.

    Keep-alive matters: without it every prod call pays a fresh TLS handshake
    and we'd be benchmarking the internet instead of the server.
    """

    def __init__(self, base_url: str, timeout: float = 360.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        parsed = urlparse(self.base_url)
        self.host = parsed.hostname
        self.port = parsed.port
        self.https = parsed.scheme == "https"
        self.conn = None

    def _connect(self):
        if self.https:
            self.conn = http.client.HTTPSConnection(
                self.host, self.port, timeout=self.timeout, context=ssl.create_default_context()
            )
        else:
            self.conn = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)

    def call(self, method: str, path: str, body=None, token: str = None):
        """Return (elapsed_ms, parsed_json). Raises ApiError on a non-2xx."""
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"

        for attempt in (1, 2):  # a dropped keep-alive socket is worth one retry
            if self.conn is None:
                self._connect()
            start = time.perf_counter()
            try:
                self.conn.request(method, path, body=payload, headers=headers)
                resp = self.conn.getresponse()
                raw = resp.read()
            except (http.client.HTTPException, OSError) as exc:
                self.close()
                if attempt == 2:
                    raise ApiError(f"{method} {path} failed: {exc}") from exc
                continue
            elapsed_ms = (time.perf_counter() - start) * 1000
            break

        if resp.status >= 300:
            raise ApiError(f"{method} {path} -> HTTP {resp.status}: {raw[:300].decode(errors='replace')}")
        try:
            return elapsed_ms, json.loads(raw) if raw else None
        except json.JSONDecodeError as exc:
            raise ApiError(f"{method} {path} -> non-JSON body: {raw[:200]!r}") from exc

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None


def rand_name(prefix: str = "bm") -> str:
    """Demo usernames: alphanumeric, <= 10 chars (enforced by the pydantic model)."""
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}{suffix}"


def find_league_id(leagues, name: str):
    # The endpoint returns a bare array today; tolerate a wrapped shape too.
    if isinstance(leagues, dict):
        leagues = leagues.get("leagues", leagues.get("data", []))
    for league in leagues or []:
        if league.get("name") == name:
            return league.get("id")
    return None


def run_suite(client: Client, admin_pw: str, inst_pw: str, num_sims: int, timings: dict, verbose=True):
    """One pass of the whole workload. Appends every measurement into `timings`."""

    def record(op, ms):
        timings.setdefault(op, []).append(ms)
        if verbose:
            print(f"    {op:<28} {ms:>9.1f} ms")
        return ms

    # --- network floor: fastest of 5 trivial round-trips ------------------
    floors = []
    for _ in range(5):
        ms, _ = client.call("GET", "/health")
        floors.append(ms)
    record("health (network floor)", min(floors))

    # --- demo phase: 2 demo submissions -----------------------------------
    for i in (1, 2):
        username = rand_name()
        ms, demo = client.call(
            "POST", "/demo/launch_demo", {"username": username, "email": f"{username}@bench.local"}
        )
        record("demo launch", ms)
        token = demo["access_token"]

        ms, leagues = client.call("GET", "/user/get-all-leagues", token=token)
        record("list leagues", ms)
        league_id = find_league_id(leagues, DEMO_LEAGUE)
        if league_id is None:
            raise ApiError(f"league '{DEMO_LEAGUE}' not found (demo launch should create it)")

        ms, assigned = client.call("POST", "/user/league-assign", {"league_id": league_id}, token=token)
        record("join league", ms)
        token = assigned["access_token"]  # refreshed token carries the new league_id

        ms, result = client.call("POST", "/user/submit-agent", {"code": AGENT_CODE}, token=token)
        record("submit agent", ms)
        # A rejected submission comes back as HTTP 400 (already raised by call()).
        # A 200 without a submission_id would mean the contract changed under us.
        if "submission_id" not in result:
            raise ApiError(f"submission {i} returned no submission_id: {result}")
        # The API times the validation run itself and reports it. That number is
        # server CPU with zero network in it - the cleanest cross-env comparison
        # we get, so keep it alongside the wall-clock measurement.
        if result.get("duration_ms") is not None:
            timings.setdefault("_val_exec", []).append(float(result["duration_ms"]))

    # --- auth phase --------------------------------------------------------
    ms, admin = client.call("POST", "/auth/admin-login", {"username": "admin", "password": admin_pw})
    record("admin login", ms)
    admin_token = admin["access_token"]

    ms, inst = client.call(
        "POST", "/auth/institution-login", {"name": INSTITUTION_NAME, "password": inst_pw}
    )
    record("institution login", ms)
    inst_token = inst["access_token"]

    # --- 3 institution actions --------------------------------------------
    ms, _ = client.call("GET", "/institution/get-all-teams", token=inst_token)
    record("get all teams", ms)

    bench_league = f"bench_{rand_name('')}"
    ms, created = client.call(
        "POST", "/institution/league-create", {"name": bench_league, "game": "greedy_pig"}, token=inst_token
    )
    record("create league", ms)
    bench_league_id = created.get("league_id")

    ms, _ = client.call("GET", "/institution/team-progress", token=inst_token)
    record("team progress", ms)

    # --- simulation: the CPU question, answered ----------------------------
    demo_league_id = league_id
    ms, sim = client.call(
        "POST",
        "/institution/run-simulation",
        {"league_id": demo_league_id, "num_simulations": num_sims},
        token=admin_token,  # admin bypasses ownership; the demo league isn't ours
    )
    record("run simulation", ms)
    agents = len(sim.get("total_points") or {})
    timings.setdefault("_sim_agents", []).append(agents)
    if verbose:
        print(f"    {'  (agents in league)':<28} {agents:>9}")

    # --- cleanup: don't leave benchmark leagues lying around in prod -------
    if bench_league_id:
        try:
            client.call("POST", "/institution/delete-league", {"league_id": bench_league_id}, token=inst_token)
        except ApiError as exc:
            print(f"    ! cleanup of league {bench_league_id} failed: {exc}", file=sys.stderr)


def benchmark(label: str, base_url: str, admin_pw: str, inst_pw: str, runs: int, num_sims: int):
    print(f"\n=== {label}: {base_url} ({runs} run{'s' if runs > 1 else ''}) ===")
    client = Client(base_url)
    timings: dict = {}
    try:
        for run in range(1, runs + 1):
            print(f"  run {run}/{runs}")
            run_suite(client, admin_pw, inst_pw, num_sims, timings)
    finally:
        client.close()
    return timings


def summarize(timings: dict, num_sims: int):
    """Collapse raw samples into medians and network-corrected server time."""
    floor = statistics.median(timings["health (network floor)"])
    agents = timings.get("_sim_agents", [0])
    summary = {
        "network_floor_ms": floor,
        "sim_agents": statistics.median(agents),
        "ops": {},
    }
    for op, samples in timings.items():
        if op.startswith("_") or op == "health (network floor)":
            continue
        median = statistics.median(samples)
        summary["ops"][op] = {
            "median_ms": median,
            "min_ms": min(samples),
            "max_ms": max(samples),
            # Server time = wall time minus the network round-trip we can't blame
            # the server for. Floored at 0.1ms so a ratio never divides by zero.
            "server_ms": max(median - floor, 0.1),
            "samples": len(samples),
        }
    # Cost of one simulated game for one agent - the only sim number that
    # survives the two environments having different numbers of demo agents.
    #
    # Normalize per run, not median-over-median: every pass leaves 2 more demo
    # teams in greedy_pig_demo (they live until the expiry sweep), so the league
    # is heavier on run 3 than on run 1 and each sample needs its own divisor.
    sim_samples = timings.get("run simulation", [])
    agent_samples = timings.get("_sim_agents", [])
    if sim_samples and agent_samples:
        per_run = [
            max(ms - floor, 0.1) / (num_sims * max(agents, 1))
            for ms, agents in zip(sim_samples, agent_samples)
        ]
        summary["sim_norm_ms"] = statistics.median(per_run)
    if timings.get("_val_exec"):
        summary["validation_exec_ms"] = statistics.median(timings["_val_exec"])
    return summary


def print_table(label: str, summary: dict):
    print(f"\n{label}")
    print(f"  network floor (min /health RTT): {summary['network_floor_ms']:.1f} ms")
    print(f"  {'operation':<24} {'median':>10} {'min':>10} {'max':>10} {'server':>10}")
    print(f"  {'-' * 24} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10}")
    for op, s in summary["ops"].items():
        print(
            f"  {op:<24} {s['median_ms']:>9.1f}m {s['min_ms']:>9.1f}m "
            f"{s['max_ms']:>9.1f}m {s['server_ms']:>9.1f}m"
        )
    if "validation_exec_ms" in summary:
        print(f"  validation exec (server-reported): {summary['validation_exec_ms']:.1f} ms")
    if "sim_norm_ms" in summary:
        print(
            f"  simulation cost: {summary['sim_norm_ms']:.3f} ms per (game x agent), "
            f"{int(summary['sim_agents'])} agents in league"
        )


def verdict(prod: dict, local: dict, num_sims: int):
    """The whole point of the script: should the server be upgraded?"""
    print("\n" + "=" * 74)
    print("COMPARISON  (server time = wall time - network floor)")
    print("=" * 74)
    print(f"  {'operation':<24} {'local':>11} {'prod':>11} {'ratio':>8}  {'verdict':<10}")
    print(f"  {'-' * 24} {'-' * 11} {'-' * 11} {'-' * 8}  {'-' * 10}")

    ratios = {}
    for op in list(local["ops"]):
        if op not in prod["ops"]:
            continue
        l_ms = local["ops"][op]["server_ms"]
        p_ms = prod["ops"][op]["server_ms"]
        ratio = p_ms / l_ms if l_ms else float("inf")
        ratios[op] = ratio
        flag = "ok" if ratio <= RATIO_HEALTHY else ("watch" if ratio <= RATIO_WATCH else "SLOW")
        print(f"  {op:<24} {l_ms:>10.1f}m {p_ms:>10.1f}m {ratio:>7.1f}x  {flag:<10}")

    # The simulation ratio has to be computed on the normalized cost: prod's demo
    # league usually holds more agents than local's, and that isn't the server's fault.
    if "sim_norm_ms" in prod and "sim_norm_ms" in local and local["sim_norm_ms"] > 0:
        ratios["run simulation"] = prod["sim_norm_ms"] / local["sim_norm_ms"]
        print(
            f"\n  simulation, per (game x agent): local {local['sim_norm_ms']:.3f} ms  "
            f"prod {prod['sim_norm_ms']:.3f} ms  -> {ratios['run simulation']:.1f}x"
        )

    # The purest CPU comparison available: the API's own stopwatch around the
    # validation run. No network, no polling overhead, no client in the way.
    if "validation_exec_ms" in prod and "validation_exec_ms" in local and local["validation_exec_ms"] > 0:
        ratios["validation exec"] = prod["validation_exec_ms"] / local["validation_exec_ms"]
        print(
            f"  validation exec (server-reported): local {local['validation_exec_ms']:.1f} ms  "
            f"prod {prod['validation_exec_ms']:.1f} ms  -> {ratios['validation exec']:.1f}x"
        )

    cpu = [ratios[op] for op in CPU_OPS if op in ratios]
    db = [ratios[op] for op in DB_OPS if op in ratios]
    cpu_ratio = statistics.median(cpu) if cpu else 0.0
    db_ratio = statistics.median(db) if db else 0.0

    # Absolute breaches: prod is slow in human terms, whatever the ratio says.
    breaches = []
    p = prod["ops"]
    for op, ceiling in (("admin login", SLOW_LOGIN_MS), ("institution login", SLOW_LOGIN_MS)):
        if op in p and p[op]["server_ms"] > ceiling:
            breaches.append(f"{op} takes {p[op]['server_ms'] / 1000:.1f}s on prod (ceiling {ceiling / 1000:.1f}s)")
    for op in DB_OPS:
        if op in p and p[op]["server_ms"] > SLOW_READ_MS:
            breaches.append(f"{op} takes {p[op]['server_ms'] / 1000:.1f}s on prod (ceiling {SLOW_READ_MS / 1000:.1f}s)")
    if "submit agent" in p and p["submit agent"]["server_ms"] > SLOW_SUBMIT_MS:
        breaches.append(
            f"submit-agent takes {p['submit agent']['server_ms'] / 1000:.1f}s on prod "
            f"(ceiling {SLOW_SUBMIT_MS / 1000:.0f}s) - students wait on this live"
        )
    if "run simulation" in p and p["run simulation"]["server_ms"] > SLOW_SIM_MS:
        breaches.append(
            f"a {num_sims}-game simulation takes {p['run simulation']['server_ms'] / 1000:.1f}s on prod "
            f"(ceiling {SLOW_SIM_MS / 1000:.0f}s)"
        )

    print("\n" + "=" * 74)
    print("SHOULD YOU UPGRADE THE SERVER?")
    print("=" * 74)
    print(f"  CPU-bound work (logins, validation, simulation): prod is {cpu_ratio:.1f}x slower than local")
    print(f"  DB-bound work  (reads and writes):               prod is {db_ratio:.1f}x slower than local")
    print(f"  Network floor:  local {local['network_floor_ms']:.1f} ms, prod {prod['network_floor_ms']:.1f} ms")
    print()

    # Order matters: an absolute breach outranks everything, then CPU, then a
    # slow DB. A slow DB gets its own verdict rather than a footnote on a clean
    # bill of health - "no upgrade needed" and "the database is 8x slow" cannot
    # both be true, and the fix for the second one isn't more vCPU anyway.
    if breaches:
        print("  VERDICT: UPGRADE. Prod is slow in absolute terms, not just relative to your laptop:")
        for b in breaches:
            print(f"    - {b}")
        print("\n  Start with vCPU/RAM on the box running the Celery workers - validation and")
        print("  simulation are the CPU-bound paths, and they're what users actually wait on.")
        if db_ratio > RATIO_WATCH:
            print(f"  Postgres is also {db_ratio:.1f}x slower than local - check storage/IOPS too.")
    elif cpu_ratio > RATIO_WATCH:
        print(f"  VERDICT: UPGRADE SOON. Prod's CPU is {cpu_ratio:.1f}x slower than your laptop.")
        print(f"  A healthy gap is under {RATIO_HEALTHY}x (a laptop core genuinely beats a cloud vCPU by")
        print(f"  2-3x). Above {RATIO_WATCH}x means the instance is undersized, and it will show up as")
        print("  slow submissions the moment a class of students submits at once.")
        print("\n  Add vCPU on the worker host first; scale the API only if DB ratio is also high.")
    elif db_ratio > RATIO_WATCH:
        print(f"  VERDICT: UPGRADE THE DATABASE, NOT THE CPU. Compute is fine ({cpu_ratio:.1f}x, inside the")
        print(f"  normal laptop-vs-cloud band), but DB work is {db_ratio:.1f}x slower than local.")
        print("  That profile is Postgres-bound: disk IO, a missing index, or a noisy-neighbour")
        print("  volume. Adding vCPU will not move it - look at storage/IOPS first.")
    elif cpu_ratio > RATIO_HEALTHY:
        print(f"  VERDICT: OK FOR NOW, WATCH IT. CPU is {cpu_ratio:.1f}x slower than local, inside the")
        print(f"  normal laptop-vs-cloud band ({RATIO_HEALTHY}-{RATIO_WATCH}x) but with little headroom.")
        print("  Re-run this under real class load; if submit-agent creeps toward")
        print(f"  {SLOW_SUBMIT_MS / 1000:.0f}s, upgrade the worker host.")
    else:
        print(f"  VERDICT: NO UPGRADE NEEDED. Prod tracks local within {cpu_ratio:.1f}x on CPU work and")
        print(f"  {db_ratio:.1f}x on DB work, and every operation is inside its absolute ceiling.")
        print("  The server is not your bottleneck today.")
    print()


def main():
    parser = argparse.ArgumentParser(description="Benchmark agent_games: prod vs local")
    parser.add_argument("--prod-url", default=DEFAULT_PROD)
    parser.add_argument("--local-url", default=DEFAULT_LOCAL)
    parser.add_argument("--runs", type=int, default=3, help="passes per environment (default 3)")
    # 2000 is deliberate. Measured locally: ~2 ms of compute per game, against a
    # fixed ~150-300 ms of overhead (task enqueue, worker process spawn - workers
    # run max_tasks_per_child=1 - result polling, saving results). At 50 games the
    # overhead IS the measurement and the agent-count normalization distorts; at
    # 2000 games compute is ~95% of the time and the number means what it says.
    parser.add_argument("--sims", type=int, default=2000, help="games per simulation (default 2000, max 10000)")
    parser.add_argument("--only", choices=["prod", "local", "both"], default="both")
    parser.add_argument("--json", help="also write raw results to this file")
    args = parser.parse_args()

    # The exported vars are the PRODUCTION secrets; local has its own (see
    # local_credentials). Only demand them when we're actually hitting prod.
    prod_admin_pw = os.environ.get("ADMIN_PASSWORD")
    prod_inst_pw = os.environ.get("INSTITUTION_PASSWORD")
    if args.only in ("prod", "both") and not (prod_admin_pw and prod_inst_pw):
        sys.exit(
            "Missing production credentials. Export both, then re-run:\n"
            "    export ADMIN_PASSWORD=...            # prod admin user\n"
            "    export INSTITUTION_PASSWORD=...      # prod 'Admin Institution'\n"
            "(Local passwords are read from the repo .env - you don't export those.)"
        )

    results = {}
    if args.only in ("local", "both"):
        local_admin_pw, local_inst_pw, source = local_credentials()
        print(f"local credentials: {source}")
        results["local"] = summarize(
            benchmark("LOCAL", args.local_url, local_admin_pw, local_inst_pw, args.runs, args.sims),
            args.sims,
        )
        print_table("LOCAL", results["local"])
    if args.only in ("prod", "both"):
        results["prod"] = summarize(
            benchmark("PROD", args.prod_url, prod_admin_pw, prod_inst_pw, args.runs, args.sims), args.sims
        )
        print_table("PROD", results["prod"])

    if "prod" in results and "local" in results:
        verdict(results["prod"], results["local"], args.sims)

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(results, fh, indent=2)
        print(f"raw results written to {args.json}")


if __name__ == "__main__":
    try:
        main()
    except ApiError as exc:
        sys.exit(f"\nBENCHMARK FAILED: {exc}")
    except KeyboardInterrupt:
        sys.exit("\ninterrupted")
