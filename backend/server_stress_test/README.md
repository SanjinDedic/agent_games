# Submission load benchmark

Measures how many greedy-pig agent submissions the site can absorb per minute,
and at what latency — so you can re-run it before/after a code change and see
the effect on capacity.

## How it works

`locust_greedy_pig.py` hammers a dedicated endpoint,
`POST /diagnostics/benchmark-submit`, which runs the **real** validator load
path (1 game + 20 greedy-pig simulations — the expensive part of
`/user/submit-agent`) but deliberately **skips**:

- the 5-submissions/min-per-team rate limit, and
- the `Submission` DB write (so the benchmark logs nothing to the database).

That isolates validator throughput, which is the thing that moves when you
change simulation/validation code.

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

### Optional env knobs

| Var | Default | Meaning |
|-----|---------|---------|
| `WAIT_MIN` / `WAIT_MAX` | `0` / `0` | per-user pause (s) between submissions; 0 = max throughput |
| `NUM_SIMULATIONS` | `20` | sims per submission (20 = prod parity) |

## Read the result (X req/min @ Y latency)

From the headless summary (or `bench_stats.csv`), the `submit_agent` row:

- **X (submissions/min)** = `Requests/s × 60`
- **Y (avg latency)** = `Average (ms)`
- watch **Failures** — non-zero means you've pushed past capacity (validator
  timeouts/queueing).
