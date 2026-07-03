# Submission load benchmark

Measures how many greedy-pig agent submissions the site can absorb per minute,
and at what latency — so you can re-run it before/after a code change and see
the effect on capacity.

Three locustfiles share the same agent payloads and summary (`bench_common.py`):

| File | Load shape | Use for |
|------|-----------|---------|
| `locust_greedy_pig.py` | weighted mix, max throughput (`-u` bound) | capacity ceiling |
| `locust_illegal_agents.py` | fixed rates: 50/min valid + 5/min *each* of spin/security/runtime, run 3 min | leak hunting under a steady illegal drip |
| `locust_legal_only.py` | fixed rate: valid only, 10 req/s, run 1 min | clean throughput/latency at a known offered load |

## How it works

`locust_greedy_pig.py` hammers a dedicated endpoint,
`POST /diagnostics/benchmark-submit`, which runs the **real** validator load
path (1 game + 20 greedy-pig simulations — the expensive part of
`/user/submit-agent`) but deliberately **skips**:

- the 5-submissions/min-per-team rate limit, and
- the `Submission` DB write (so the benchmark logs nothing to the database).

That isolates validator throughput, which is the thing that moves when you
change simulation/validation code.

## Agent mix (problematic agents included)

By default the load is not all valid agents. The locustfile sends a weighted
mix, each type recorded under its own row in the summary, so the bad agents
exercise the validator's reject / timeout / kill paths — the paths where a
CPU-spin regression hides. (A timed-out agent that isn't fully killed leaves a
core pegged at 100%.)

| Row (`name`)           | Agent code                          | Path exercised        | Expected |
|------------------------|-------------------------------------|-----------------------|----------|
| `submit_valid`         | randomized threshold strategy       | full success          | success  |
| `submit_slow`          | heavy finite loop, under the 5s cap | worker CPU pressure   | success  |
| `submit_spin`          | `while True: pass`                  | 5s timeout + kill     | rejected |
| `submit_security`      | `import os` / `eval(...)`           | AST reject in parent  | rejected |
| `submit_runtime_error` | divide-by-zero in `__init__`        | child error path      | rejected |

**The "failures" on `submit_spin` / `submit_security` / `submit_runtime_error`
rows are EXPECTED** — those agents are supposed to be rejected. The locustfile
counts the opposite (a bad agent that *validated*) as the failure. Read
`submit_valid` (and `submit_slow`) for clean throughput/latency.

Each spin agent holds a validator child slot for the full ~5s timeout, so even a
small `W_SPIN` throttles everything behind the `_MAX_PROCS` semaphore — that's
realistic backpressure. Set `W_SPIN=0` to reproduce the old pure-valid run.

## CPU check (no core at 100%)

The throughput number won't tell you if a killed agent leaked a runaway process.
The signature of that bug is **residual CPU after the load stops**: the validator
should fall back to idle. `monitor_cpu.sh` watches for exactly that.

Local stack only (it reads `docker stats` on this host). In a second terminal:

```bash
cd backend/server_stress_test
./monitor_cpu.sh            # Ctrl-C after the benchmark finishes for the verdict
```

It prints each container's peak CPU during the run and its idle CPU from the
final samples, then a PASS/FAIL: a container still above the idle threshold (25%
by default) once traffic stops ⇒ `FAIL` (likely a leaked spinner — confirm with
`docker top <container>`). Knobs: `INTERVAL`, `IDLE_THRESHOLD`, `IDLE_SAMPLES`,
`MATCH`.

## Safety gate

The endpoint is **disabled by default**. It only works when the API process has
`BENCHMARK_TOKEN` set in its environment, and the request carries a matching
`X-Benchmark-Token` header. No env var ⇒ every call returns 403-style error.

To benchmark prod: set `BENCHMARK_TOKEN=<secret>` in the API deploy env, run the
benchmark, then **unset it** when done. Never leave it enabled in normal
operation — it bypasses the rate limit.

## Run it

Install locust locally (not needed in any container): `pip install locust`.

```bash
BENCHMARK_TOKEN=<same-secret-as-api> \
locust -f backend/server_stress_test/locust_greedy_pig.py \
    --headless -u 50 -r 1 -t 2m \
    --host https://your-prod-host \
    --csv bench
```

- `-u` total concurrent users, `-r` spawn rate/s, `-t` duration.
- Start low (`-u 20`) and step up until latency climbs or failures appear —
  that knee is your capacity ceiling.

### Fixed-rate runs

The two fixed-rate tests pace each user with `constant_throughput`, so `-u`
must match the fixed user counts the file defines (a mismatch logs a warning
and skews the offered rate):

```bash
# Illegal drip: 50/min valid + 5/min each of spin/security/runtime, 3 minutes
BENCHMARK_TOKEN=<secret> \
locust -f backend/server_stress_test/locust_illegal_agents.py \
    --headless -u 9 -r 9 -t 3m --host https://your-prod-host --csv bench_illegal

# Legal only: 10 submissions/s for 1 minute
BENCHMARK_TOKEN=<secret> \
locust -f backend/server_stress_test/locust_legal_only.py \
    --headless -u 30 -r 30 -t 1m --host https://your-prod-host --csv bench_legal
```

Rates/user counts are env-tunable: `LEGAL_PER_MIN`, `ILLEGAL_PER_MIN`,
`VALID_USERS`, `SPIN_USERS`, `SECURITY_USERS`, `RUNTIME_USERS` (illegal test);
`TARGET_RPS`, `USERS` (legal test). Pacing can only *cap* the rate — if latency
exceeds a user's interval the achieved rate falls below target, which is itself
the finding. Run `monitor_cpu.sh` alongside the illegal test.

### Optional env knobs

| Var | Default | Meaning |
|-----|---------|---------|
| `WAIT_MIN` / `WAIT_MAX` | `0` / `0` | per-user pause (s) between submissions; 0 = max throughput |
| `NUM_SIMULATIONS` | `20` | sims per submission (20 = prod parity) |
| `W_VALID` | `80` | weight of valid agents in the mix |
| `W_SPIN` | `3` | weight of infinite-loop (timeout) agents; `0` = pure valid run |
| `W_SLOW` | `7` | weight of heavy-but-legal agents (finish under the 5s cap) |
| `W_SECURITY` | `5` | weight of AST-rejected agents (`import os` / `eval`) |
| `W_RUNTIME` | `5` | weight of runtime-error agents (divide-by-zero) |

## Read the result (X req/min @ Y latency)

From the headless summary (or `bench_stats.csv`), the `submit_agent` row:

- **X (submissions/min)** = `Requests/s × 60`
- **Y (avg latency)** = `Average (ms)`
- watch **Failures** — non-zero means you've pushed past capacity (validator
  timeouts/queueing).
