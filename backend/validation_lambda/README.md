# Agent-validation Lambda

Server-side execution for agent submission validation. Validation runs
**Pyodide-first in the browser**; this folder serves the traffic that
structurally cannot: hint requests (`generate_hint=true` — the hint context
needs a fresh server-run envelope), `VITE_PYODIDE_VALIDATION=false` builds,
and browser-fallback traffic (tagged `execution_source="pyodide_fallback"`,
counted at `GET /diagnostics/pyodide-fallbacks` with a `validation:` reason
prefix). It replaced the Celery `worker-validation` container.

**Unlike `backend/fallback_lambda/`, this folder is permanent infra** — the
hint path can never move to the browser, so there is no delete-when-telemetry-
zero end state here.

## Layout

| File | Runs where | Purpose |
|---|---|---|
| `executor.py` | Lambda + local subprocess + tests | Execution core (task semantics, 7-key envelope, 5s soft / 6s hard limits, fork isolation). Pinned against the browser harness by `backend/tests/unit/test_validation_harness_parity.py`. |
| `handler.py` | Lambda + local subprocess | Event dispatch; `lambda_handler` is the Lambda entry point. |
| `local_run.py` | local subprocess | stdin JSON event → stdout JSON envelope. Installs the stdlib `backend.config` stub first — the real config `load_dotenv`s secrets at import time. |
| `client.py` | API only (not shipped in the zip) | Async client the routes call. `VALIDATION_LAMBDA_FUNCTION` set → boto3 invoke; unset → local subprocess with a scrubbed env. |
| `deploy.sh` | your Mac | Idempotent create-or-update via aws CLI; stages the zip (modules + `backend/games/**` + a generated `config.py` stub). |

`executor.py`, `handler.py`, `local_run.py` must import nothing beyond the
stdlib and `backend.games.*` — the zip ships no dependencies and the local
runner runs with a scrubbed environment. The AST safety gate stays in the
API process (`backend/routes/user/code_validation.py`); this sandbox is the
second wall, not the first.

## Deploy

```bash
aws-vault exec <admin-profile> -- ./backend/validation_lambda/deploy.sh --smoke
```

Creates on first run (region ap-southeast-2):
- IAM role `agent-games-validation-role` — trust `lambda.amazonaws.com`,
  `AWSLambdaBasicExecutionRole` only (logs; the sandbox holds no other permission)
- Lambda `agent-games-validation` — python3.14/arm64 (same interpreter as the
  backend image), **1769MB** (Lambda CPU scales with memory; 1769MB = 1 vCPU,
  and the per-game `validation_simulations` counts were benchmarked on
  cpus:1.0), 8s timeout, reserved concurrency 10

Redeploy after adding a game — the zip snapshots `backend/games/`; the
generated config stub rediscovers games at import, so nothing else changes.

`--smoke` invokes pass/construction-error/spinner payloads and asserts the
envelope shapes and the exact timeout message.

## Wiring the API (prod)

1. The API's IAM user needs exactly one extra permission:
   `lambda:InvokeFunction` on
   `arn:aws:lambda:ap-southeast-2:<account>:function:agent-games-validation`.
2. `config/deploy.yml` sets `VALIDATION_LAMBDA_FUNCTION: agent-games-validation`
   in the clear env. Unset it to fall back to local subprocess mode
   (emergency degraded mode — works, logs a warning, runs inside the API
   container's limits; full game simulations are heavier than exercise runs,
   so treat it as a stopgap, not a steady state).

Dev and CI never set `VALIDATION_LAMBDA_FUNCTION`: everything runs through
the local subprocess path, no AWS involved.
