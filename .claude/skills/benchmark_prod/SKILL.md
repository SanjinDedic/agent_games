---
name: benchmark_prod
description: Benchmark production against local — same workload on both, network-corrected — to answer whether the production server is underpowered and should be upgraded. Use when asked how fast prod is, whether the site feels slow, whether to upgrade/resize the server, or to compare prod vs local performance.
---

# Prod vs local speed benchmark

One question: **is the production server underpowered?** `benchmark.py` runs the same
workload against prod and local, corrects for network latency, and prints a verdict.
Stdlib-only Python — no venv, no pip, no Playwright. Runs straight off the host.

## Run it

```bash
export ADMIN_PASSWORD=...          # PROD admin user
export INSTITUTION_PASSWORD=...    # PROD "Admin Institution"

python3 .claude/skills/benchmark_prod/benchmark.py               # both envs, 3 runs each
python3 .claude/skills/benchmark_prod/benchmark.py --only local  # no prod creds needed
python3 .claude/skills/benchmark_prod/benchmark.py --runs 5 --json out.json
```

The exported vars are the **production** secrets. Local passwords are read from the
repo's committed `.env` (`LOCAL_ADMIN_PASSWORD` / `LOCAL_INSTITUTION_PASSWORD` override
them) — if one pair were used for both, the local half would try prod credentials against
localhost and 401. The local half needs the stack up (`docker compose up -d`; see
`tester_skill` for a clean start).

The verdict only prints when both environments ran — `--only prod` gives timings, not a
recommendation, because there's nothing to compare against.

## What it measures

Per environment: 2 demo submissions (launch → join `greedy_pig_demo` → submit-agent),
admin + institution login, 3 institution actions (get-all-teams, league-create,
team-progress), and a `run-simulation` over the demo league.

- **Network floor** — fastest of 5 `/health` round-trips, subtracted from every prod
  timing. Without it you'd blame the server for the trip to Sydney.
- **CPU ratio** — decides the verdict. Logins (bcrypt), validation, and simulation are
  CPU-bound. A laptop core genuinely beats a cloud vCPU by 2–3×, so ≤2.5× is healthy,
  ≤4× is watch, >4× says undersized.
- **DB ratio** — reported separately so slow Postgres (IOPS, missing index) isn't
  misdiagnosed as a slow CPU. It gets its own verdict; more vCPU won't fix it.
- **Absolute ceilings** — breaching one (submit-agent >5s, login >1.5s, sim >30s) means
  upgrade regardless of ratio: a fast laptop doesn't excuse a slow server.
- **validation exec** — the API's own stopwatch around the validation run (`duration_ms`
  in the response). Purest CPU probe: no network, no polling.

## It writes to production

Each pass creates 2 demo teams (left to the app's own expiry sweep), creates a benchmark
league (deleted at the end of the pass), and saves a simulation result on the demo league.
Say so before running it against prod if the user didn't explicitly ask for that.

## Gotchas baked into the script

- **Don't lower `--sims` to make the run faster** (default 2000). A simulation carries
  ~150–300 ms of fixed overhead (enqueue, worker process spawn —
  `worker_max_tasks_per_child=1` — polling, saving results) on top of ~2 ms of compute
  per game. Below ~500 games the overhead *is* the measurement and the agent-count
  normalization distorts it. You'd be benchmarking the queue, not the CPU.
- Each pass leaves 2 demo teams in `greedy_pig_demo`, so the league gets heavier run over
  run — and prod usually holds more demo agents than local. Simulation cost is therefore
  normalized **per run** to ms per (game × agent); raw wall-clock sim time is not
  comparable across environments on its own.
- `run-simulation` uses the **admin** token: the demo league belongs to the Demo
  Institution and only admin bypasses the ownership check. That's why both passwords are
  needed.
- A rejected submission returns HTTP 400; success is a 200 carrying `submission_id`.
- Keep-alive is deliberate — without it every prod call pays a fresh TLS handshake and the
  numbers measure the internet, not the server.

## Report

Lead with the verdict and the two ratios (CPU, DB), then the network floor. If the verdict
is UPGRADE, name the specific breaches — the ceilings are what a user actually feels.
Local reference baseline (Apple silicon, 2026-07): logins ~190 ms, submit-agent ~324 ms
(validation exec ~235 ms), DB reads 2–6 ms, 2000-game simulation ~5.1 s.
