#!/usr/bin/env bash
# Idempotent deploy of the exercise-fallback Lambda.
#
#   aws-vault exec <admin-profile> -- ./backend/fallback_lambda/deploy.sh [--smoke]
#
# Creates the IAM role on first run (logs-only: the sandbox guarantee is an
# execution role with zero permissions beyond CloudWatch), then creates or
# updates the function from a zip of the stdlib-only modules in this folder.
# client.py is deliberately excluded — it imports boto3 and never ships.
#
# --smoke invokes four payloads and asserts the envelopes, including the
# exact timeout message for a spinner.
set -euo pipefail

FUNCTION_NAME="agent-games-exercise-fallback"
ROLE_NAME="agent-games-exercise-fallback-role"
REGION="ap-southeast-2"
# Matches the backend image (python:3.14-alpine) — no interpreter skew
# between the API, the tests, and the deployed function.
RUNTIME="python3.14"
ARCH="arm64"
# 1769MB = 1 full vCPU on Lambda (CPU scales with memory). The 0.5s soft
# limit is wall-clock and the old worker had cpus:1.0 — less memory here
# means less CPU and false timeouts, not just less RAM.
MEMORY_MB=1769
TIMEOUT_S=3
RESERVED_CONCURRENCY=10
HANDLER="backend.fallback_lambda.handler.lambda_handler"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ZIP_FILE="$(mktemp -d)/fallback_lambda.zip"

echo "==> Zipping (stdlib-only modules, package path preserved)"
(
  cd "$REPO_ROOT"
  zip -q "$ZIP_FILE" \
    backend/__init__.py \
    backend/fallback_lambda/__init__.py \
    backend/fallback_lambda/executor.py \
    backend/fallback_lambda/handler.py \
    backend/fallback_lambda/local_run.py
)

echo "==> Ensuring IAM role $ROLE_NAME"
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }' >/dev/null
  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  echo "    created (waiting for propagation)"
fi
ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)"

if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "==> Updating $FUNCTION_NAME"
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --runtime "$RUNTIME" \
    --handler "$HANDLER" \
    --memory-size "$MEMORY_MB" \
    --timeout "$TIMEOUT_S" \
    --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
else
  echo "==> Creating $FUNCTION_NAME"
  # Fresh roles take a few seconds to become assumable by Lambda.
  for attempt in $(seq 1 10); do
    if aws lambda create-function \
      --function-name "$FUNCTION_NAME" \
      --runtime "$RUNTIME" \
      --architectures "$ARCH" \
      --handler "$HANDLER" \
      --role "$ROLE_ARN" \
      --memory-size "$MEMORY_MB" \
      --timeout "$TIMEOUT_S" \
      --zip-file "fileb://$ZIP_FILE" \
      --region "$REGION" >/dev/null 2>&1; then
      break
    fi
    if [ "$attempt" -eq 10 ]; then
      echo "create-function failed after 10 attempts" >&2
      exit 1
    fi
    echo "    role not assumable yet, retrying (${attempt}/10)"
    sleep 3
  done
  aws lambda wait function-active --function-name "$FUNCTION_NAME" --region "$REGION"
fi

aws lambda put-function-concurrency \
  --function-name "$FUNCTION_NAME" \
  --reserved-concurrent-executions "$RESERVED_CONCURRENCY" \
  --region "$REGION" >/dev/null

echo "==> Deployed $FUNCTION_NAME ($RUNTIME/$ARCH, ${MEMORY_MB}MB, ${TIMEOUT_S}s, concurrency $RESERVED_CONCURRENCY)"

if [ "${1:-}" != "--smoke" ]; then
  exit 0
fi

echo "==> Smoke tests"
OUT_DIR="$(mktemp -d)"

invoke() {
  aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --cli-binary-format raw-in-base64-out \
    --payload "$1" \
    --region "$REGION" \
    "$2" >/dev/null
}

invoke '{"kind":"exercise","code":"def add(a, b):\n    return a + b\n","entry_function":"add","test_code":"def test_add():\n    check(add(1, 2), 3)\n"}' "$OUT_DIR/pass.json"
invoke '{"kind":"exercise","code":"def add(a, b):\n    return a - b\n","entry_function":"add","test_code":"def test_add():\n    check(add(1, 2), 3)\n"}' "$OUT_DIR/fail.json"
invoke '{"kind":"snippet","code":"print(\"hello\")"}' "$OUT_DIR/snippet.json"
START=$(date +%s)
invoke '{"kind":"exercise","code":"while True:\n    pass\n","entry_function":"","test_code":"def test_x():\n    check(1, 1)\n"}' "$OUT_DIR/spin.json"
SPIN_SECS=$(( $(date +%s) - START ))

python3 - "$OUT_DIR" "$SPIN_SECS" <<'PY'
import json, sys
out_dir, spin_secs = sys.argv[1], int(sys.argv[2])
exercise_keys = {"status", "message", "passed", "test_results", "duration_ms", "traceback", "stdout"}
snippet_keys = {"status", "message", "stdout", "traceback", "duration_ms"}
timeout_msg = ("Your code consumes too much time - the tests did not finish "
               "within 0.5 seconds. It may be stuck in a loop.")

def load(name):
    with open(f"{out_dir}/{name}.json") as f:
        return json.load(f)

r = load("pass")
assert set(r) == exercise_keys and r["status"] == "success" and r["passed"], r
r = load("fail")
assert set(r) == exercise_keys and r["status"] == "success" and not r["passed"], r
r = load("snippet")
assert set(r) == snippet_keys and r["status"] == "success" and r["stdout"] == "hello\n", r
r = load("spin")
assert set(r) == exercise_keys and r["status"] == "error", r
assert r["message"] == timeout_msg, r["message"]
assert spin_secs <= 4, f"spinner took {spin_secs}s (hard kill not working?)"
print("smoke tests passed")
PY
