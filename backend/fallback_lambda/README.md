# Exercise/snippet fallback Lambda

Server-side execution fallback for tutorial exercises and lesson snippets.
Both run **Pyodide-first in the browser**; this folder only serves traffic
the browser could not run (tagged `execution_source="pyodide_fallback"`,
counted at `GET /diagnostics/pyodide-fallbacks`) and `VITE_PYODIDE_EXERCISES=false`
builds. It replaced the Celery `worker-exercises` container.

**This folder is designed to be deleted.** Once the fallback telemetry shows
a sustained zero, remove the folder, the four call sites that import
`client.py`, and the Lambda + IAM pieces below.

## Layout

| File | Runs where | Purpose |
|---|---|---|
| `executor.py` | Lambda + local subprocess + tests | Execution core (harness semantics, envelopes, 0.5s soft / 1.5s hard limits, fork isolation). Pinned against the browser harness by `backend/tests/unit/test_exercise_harness_parity.py`. |
| `handler.py` | Lambda + local subprocess | Event dispatch; `lambda_handler` is the Lambda entry point. |
| `local_run.py` | local subprocess | stdin JSON event → stdout JSON envelope. |
| `client.py` | API only (not shipped in the zip) | Async client the routes call. `EXERCISE_LAMBDA_FUNCTION` set → boto3 invoke; unset → local subprocess with a scrubbed env. |
| `deploy.sh` | your Mac | Idempotent create-or-update via aws CLI. |

`executor.py`, `handler.py`, `local_run.py` must stay **stdlib-only** — the
zip ships no dependencies and the local runner runs with a scrubbed
environment.

## Deploy

```bash
aws-vault exec <admin-profile> -- ./backend/fallback_lambda/deploy.sh --smoke
```

Creates on first run (region ap-southeast-2):
- IAM role `agent-games-exercise-fallback-role` — trust `lambda.amazonaws.com`,
  `AWSLambdaBasicExecutionRole` only (logs; the sandbox holds no other permission)
- Lambda `agent-games-exercise-fallback` — python3.14/arm64 (same interpreter
  as the backend image), **1769MB**
  (Lambda CPU scales with memory; 1769MB = 1 vCPU, needed so the 0.5s
  wall-clock budget means what it meant on the worker), 3s timeout,
  reserved concurrency 10

`--smoke` invokes pass/fail/snippet/spinner payloads and asserts the
envelope shapes and the exact timeout message.

## Wiring the API (prod)

1. The API's IAM user needs exactly one extra permission:
   `lambda:InvokeFunction` on
   `arn:aws:lambda:ap-southeast-2:<account>:function:agent-games-exercise-fallback`.
2. `config/deploy.yml` sets `EXERCISE_LAMBDA_FUNCTION: agent-games-exercise-fallback`
   in the clear env. Unset it to fall back to local subprocess mode (emergency
   degraded mode — works, logs a warning, runs inside the API container's
   limits).

Dev and CI never set `EXERCISE_LAMBDA_FUNCTION`: everything runs through the
local subprocess path, no AWS involved.

## Deleting (the goal)

1. Confirm `GET /diagnostics/pyodide-fallbacks` shows a sustained zero.
2. Decide the fate of the untagged server path (`VITE_PYODIDE_EXERCISES=false`
   builds and the `/tutorial/admin/run-exercise` dry run) — they use this
   fallback too.
3. Delete this folder, the imports in `tutorial_router.py`, `lesson_router.py`,
   `tutorial_models.py` (MAX_STDOUT_CHARS), the parity test's `worker` import
   target, `EXERCISE_LAMBDA_FUNCTION` from `config/deploy.yml`.
4. `aws lambda delete-function`, `aws iam delete-role` (detach the managed
   policy first), drop the `lambda:InvokeFunction` policy from the API user.
