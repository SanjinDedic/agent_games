#!/usr/bin/env bash
# Idempotent deploy of the exercise-fallback Lambda.
#
#   EXEC_JWT_SECRET=... aws-vault exec <admin-profile> -- ./backend/fallback_lambda/deploy.sh [--smoke]
#
# Creates the IAM role on first run (logs + VPC-ENI management only: the
# sandbox guarantee is an execution role with no other permissions), then
# creates or updates the function from a zip of the stdlib-only modules in
# this folder. client.py is deliberately excluded — it imports boto3 and
# never ships.
#
# The function is locked into a dedicated VPC with NO internet gateway and a
# security group with zero egress rules: student code cannot open any
# outbound connection. Invoke payload/response and CloudWatch logs travel
# over the Lambda control plane, not the VPC ENI, so the function still
# works. A Function URL (auth NONE + in-handler EXEC_JWT_SECRET check) lets
# the browser call it directly.
#
# --smoke invokes four payloads and asserts the envelopes (including the
# exact timeout message for a spinner), proves egress is blocked, and
# exercises the Function URL with a freshly minted token plus a bad one.
set -euo pipefail

: "${EXEC_JWT_SECRET:?Set EXEC_JWT_SECRET in the deploy environment (must match the API value)}"

FUNCTION_NAME="agent-games-exercise-fallback"
ROLE_NAME="agent-games-exercise-fallback-role"
REGION="ap-southeast-2"
VPC_NAME="agent-games-lambda-lockdown"
VPC_CIDR="10.66.0.0/24"
SG_NAME="agent-games-no-egress"
# Browser origins allowed to call the Function URL (preflight handled by the
# URL's CORS config, never by the handler).
CORS_ORIGINS='["https://agentgames.io","https://www.agentgames.io","http://localhost:3000"]'
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
    backend/fallback_lambda/exec_token.py \
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
# ENI management for VPC attachment (idempotent). This is the only
# permission beyond CloudWatch logs; the ENI is created at config time, not
# per-invoke.
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
ROLE_ARN="$(aws iam get-role --role-name "$ROLE_NAME" --query Role.Arn --output text)"

echo "==> Ensuring no-egress VPC $VPC_NAME"
VPC_ID="$(aws ec2 describe-vpcs --region "$REGION" \
  --filters "Name=tag:Name,Values=$VPC_NAME" \
  --query 'Vpcs[0].VpcId' --output text)"
if [ "$VPC_ID" = "None" ]; then
  VPC_ID="$(aws ec2 create-vpc --region "$REGION" --cidr-block "$VPC_CIDR" \
    --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$VPC_NAME}]" \
    --query Vpc.VpcId --output text)"
  echo "    created $VPC_ID (no internet gateway, ever)"
fi

AZS=($(aws ec2 describe-availability-zones --region "$REGION" \
  --query 'AvailabilityZones[0:2].ZoneName' --output text))
SUBNET_IDS=()
i=0
for CIDR in 10.66.0.0/25 10.66.0.128/25; do
  NAME="$VPC_NAME-subnet-$i"
  SUBNET_ID="$(aws ec2 describe-subnets --region "$REGION" \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$NAME" \
    --query 'Subnets[0].SubnetId' --output text)"
  if [ "$SUBNET_ID" = "None" ]; then
    SUBNET_ID="$(aws ec2 create-subnet --region "$REGION" --vpc-id "$VPC_ID" \
      --cidr-block "$CIDR" --availability-zone "${AZS[$i]}" \
      --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$NAME}]" \
      --query Subnet.SubnetId --output text)"
    echo "    created subnet $SUBNET_ID (${AZS[$i]})"
  fi
  SUBNET_IDS+=("$SUBNET_ID")
  i=$((i + 1))
done

SG_ID="$(aws ec2 describe-security-groups --region "$REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=$SG_NAME" \
  --query 'SecurityGroups[0].GroupId' --output text)"
if [ "$SG_ID" = "None" ]; then
  SG_ID="$(aws ec2 create-security-group --region "$REGION" --vpc-id "$VPC_ID" \
    --group-name "$SG_NAME" \
    --description "Zero egress: student code cannot SYN anywhere" \
    --query GroupId --output text)"
  echo "    created security group $SG_ID"
fi
# Strip the default allow-all egress rule; NotFound on re-runs is fine.
aws ec2 revoke-security-group-egress --region "$REGION" --group-id "$SG_ID" \
  --ip-permissions '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]' \
  >/dev/null 2>&1 || true
VPC_CONFIG="SubnetIds=$(IFS=,; echo "${SUBNET_IDS[*]}"),SecurityGroupIds=$SG_ID"

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
    --vpc-config "$VPC_CONFIG" \
    --environment "Variables={EXEC_JWT_SECRET=$EXEC_JWT_SECRET}" \
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
      --vpc-config "$VPC_CONFIG" \
      --environment "Variables={EXEC_JWT_SECRET=$EXEC_JWT_SECRET}" \
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

echo "==> Ensuring Function URL (auth NONE — the handler enforces the exec token)"
CORS_JSON="{\"AllowOrigins\":$CORS_ORIGINS,\"AllowMethods\":[\"POST\"],\"AllowHeaders\":[\"authorization\",\"content-type\"],\"MaxAge\":86400}"
if aws lambda get-function-url-config --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-url-config \
    --function-name "$FUNCTION_NAME" \
    --auth-type NONE \
    --cors "$CORS_JSON" \
    --region "$REGION" >/dev/null
else
  aws lambda create-function-url-config \
    --function-name "$FUNCTION_NAME" \
    --auth-type NONE \
    --cors "$CORS_JSON" \
    --region "$REGION" >/dev/null
fi
# Public invoke permission for the URL; already-exists on re-runs is fine.
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id public-function-url \
  --action lambda:InvokeFunctionUrl \
  --principal '*' \
  --function-url-auth-type NONE \
  --region "$REGION" >/dev/null 2>&1 || true
FUNCTION_URL="$(aws lambda get-function-url-config --function-name "$FUNCTION_NAME" \
  --region "$REGION" --query FunctionUrl --output text)"

echo "==> Deployed $FUNCTION_NAME ($RUNTIME/$ARCH, ${MEMORY_MB}MB, ${TIMEOUT_S}s, concurrency $RESERVED_CONCURRENCY)"
echo "==> Function URL (set VITE_EXERCISE_LAMBDA_URL to this): $FUNCTION_URL"

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

# Egress-block proof: a raw TCP connect to a public IP must fail — the VPC
# has no route out. DNS still resolves (VPC-internal service), so test the
# connection itself, not a lookup.
invoke '{"kind":"snippet","code":"import socket\ns = socket.create_connection((\"1.1.1.1\", 80), timeout=0.3)\nprint(\"CONNECTED\")"}' "$OUT_DIR/egress.json"

echo "==> Function URL smoke (minted token + bad token)"
EXEC_TOKEN="$(EXEC_JWT_SECRET="$EXEC_JWT_SECRET" python3 - <<'PY'
import base64, hashlib, hmac, json, os, time

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
payload = b64url(json.dumps(
    {"sub": "smoke", "scope": "exec", "exp": int(time.time()) + 30}
).encode())
sig = b64url(hmac.new(os.environ["EXEC_JWT_SECRET"].encode(),
                      f"{header}.{payload}".encode(), hashlib.sha256).digest())
print(f"{header}.{payload}.{sig}")
PY
)"
URL_STATUS="$(curl -s -o "$OUT_DIR/url_pass.json" -w '%{http_code}' \
  -X POST "$FUNCTION_URL" \
  -H "Authorization: Bearer $EXEC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kind":"snippet","code":"print(\"via url\")"}')"
URL_BAD_STATUS="$(curl -s -o /dev/null -w '%{http_code}' \
  -X POST "$FUNCTION_URL" \
  -H "Authorization: Bearer not.a.token" \
  -H "Content-Type: application/json" \
  -d '{"kind":"snippet","code":"print(\"nope\")"}')"

python3 - "$OUT_DIR" "$SPIN_SECS" "$URL_STATUS" "$URL_BAD_STATUS" <<'PY'
import json, sys
out_dir, spin_secs = sys.argv[1], int(sys.argv[2])
url_status, url_bad_status = sys.argv[3], sys.argv[4]
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
r = load("egress")
assert r["status"] == "error", f"egress NOT blocked: {r}"
assert "CONNECTED" not in (r.get("stdout") or ""), f"egress NOT blocked: {r}"
assert url_status == "200", f"Function URL returned {url_status}"
r = load("url_pass")
assert set(r) == snippet_keys and r["stdout"] == "via url\n", r
assert url_bad_status == "401", f"bad token returned {url_bad_status}, wanted 401"
print("smoke tests passed (envelopes, egress block, function URL)")
PY
