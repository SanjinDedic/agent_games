# Exercises load benchmark

Measures how many tutorial-exercise runs the site can absorb per minute, and at
what latency — the exercises counterpart of the submission benchmark
([README.md](README.md)).

## How it works

`locust_exercises.py` logs in as **admin** once per user (`on_start`) and then
hammers `POST /tutorial/admin/run-exercise` — the admin editor's stateless
"dry run". That endpoint runs the **real** exercise fallback path:

```
API → backend/fallback_lambda/ (Lambda in prod, local subprocess in dev) → envelope
```

The runner is the sandbox (no secrets/DB/S3, fresh forked child per run,
process-group SIGKILL) under a **0.5s soft / 1.5s hard** time limit.
run-exercise deliberately has **no DB write** and **no rate limit**, so it
isolates the run throughput — exactly what the submission benchmark's gated
endpoint does, but exercises already ship one, so no benchmark token is
needed; an admin login is.

> **No AST safety gate.** Unlike agent submissions, exercise code is *not*
> statically checked before it runs — the isolated runner is the sandbox. That
> is why the timeout / kill path (`ex_timeout`) is the most important one to
> load: the 1.5s hard process-group `SIGKILL` reaping a spinner is the safety
> boundary.

## Exercise mix

The load is a weighted mix, each type recorded under its own summary row so the
runner's distinct paths are all exercised:

| Row (`name`)  | Exercise code                     | Path exercised                | Expected |
|---------------|-----------------------------------|-------------------------------|----------|
| `ex_valid`    | correct `solve`, passes checks    | full success                  | success, passed |
| `ex_wrong`    | runs but returns wrong answer     | success path, failing checks  | success, not passed |
| `ex_slow`     | heavy finite loop under 0.5s      | runner CPU pressure           | success  |
| `ex_timeout`  | `while True: pass`                | 0.5s soft → 1.5s hard SIGKILL | error    |
| `ex_error`    | module-level `x = k / 0`          | fast exec-failure path        | error    |

**The "failures" on `ex_timeout` / `ex_error` are EXPECTED** — those runs are
supposed to come back with an `error` status (the runner kills / rejects them).
The locustfile counts the *opposite* (a spinner that returned `success`, i.e.
was never killed) as the failure. Read `ex_valid` (and `ex_slow`) for clean
throughput / latency.

In local-runner mode each `ex_timeout` run holds one of the client's bounded
subprocess slots for the full hard-kill window, so even a small `W_TIMEOUT`
throttles everything behind it — realistic backpressure. Set `W_TIMEOUT=0` for
a pure-legal run.

## CPU / leak check (no core stuck at 100%)

The throughput number won't tell you whether a killed exercise leaked a runaway
process. The signature is **residual CPU after the load stops**. In local-runner
mode the runs execute inside the **api** container, so point `monitor_cpu.sh`
there:

```bash
cd backend/server_stress_test
MATCH=api ./monitor_cpu.sh   # Ctrl-C after the run for the verdict
```

Local stack only (it reads `docker stats`). A container still above the idle
threshold once traffic stops ⇒ `FAIL` (likely a leaked spinner — confirm with
`docker top <container>`). Against prod (Lambda mode) check CloudWatch Duration
/ Errors instead.

## Run it

Containerized (no local locust needed), against the local stack:

```bash
cd backend/server_stress_test
docker compose run --rm benchmark-exercises
# push harder / longer:
USERS=40 DURATION=2m docker compose run --rm benchmark-exercises
```

Or with a local locust install:

```bash
locust -f backend/server_stress_test/locust_exercises.py \
    --headless -u 20 -r 2 -t 1m \
    --host http://localhost:8000 --csv bench_exercises
```

- `-u` total concurrent users, `-r` spawn rate/s, `-t` duration. Start low and
  step up until latency climbs or `ex_valid` failures appear — that knee is the
  capacity ceiling.
- `--host` must be a stack whose admin password you know: the default
  `ADMIN_USERNAME`/`ADMIN_PASSWORD` is `admin`/`admin` (the committed dev
  default). Override both for a remote stack.

### Env knobs

| Var | Default | Meaning |
|-----|---------|---------|
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin` | admin login for run-exercise |
| `WAIT_MIN` / `WAIT_MAX` | `0` / `0` | per-user pause (s) between runs; 0 = max throughput |
| `W_VALID` | `80` | weight of correct exercises |
| `W_WRONG` | `8` | weight of wrong-answer (still a clean run) exercises |
| `W_SLOW` | `4` | weight of heavy-but-legal exercises |
| `W_TIMEOUT` | `3` | weight of infinite-loop (timeout) exercises; `0` = pure legal run |
| `W_ERROR` | `5` | weight of module-level-error exercises |
| `SLOW_ITERS_MIN` / `MAX` | `200000` / `400000` | `ex_slow` loop size; lower if the host trips the 0.5s limit |

## Read the result

From the headless summary (or `bench_exercises_stats.csv`), the `ex_valid` row:

- **runs/min** = `Requests/s × 60`
- **latency** = `Average (ms)` / `p95`
- watch **failures** on `ex_valid` / `ex_slow` — non-zero means you've pushed
  past capacity (the two-slot worker is queueing, and legal runs are tipping
  over the 0.5s soft limit).
