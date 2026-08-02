"""API-side client for server-side agent validation.

The only module the routes import. Two modes, switched solely on whether
VALIDATION_LAMBDA_FUNCTION is set (never on credential presence — dev's .env
carries MinIO creds that must not flip this switch):

- **Lambda mode** (env set, production): boto3 ``invoke`` of the function
  deployed from this folder (deploy.sh). Retries are OFF — a retry re-runs
  agent code — and the read timeout sits just past the function's own 8s
  ceiling.
- **Local mode** (env unset, dev/CI default): a fresh ``sys.executable``
  subprocess running local_run.py with a scrubbed environment, bounded by a
  semaphore so a submission burst can't fork-storm the API container.

Every failure mode maps to a normalized envelope — routes never see an
exception. A run that produced no result (function timeout, OOM, dead
subprocess) collapses to the canonical timeout envelope, the same collapse
the old Celery path made for TimeLimitExceeded/WorkerLostError.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from backend.validation_lambda.executor import (
    normalize_result,
    timeout_validation_result,
)

logger = logging.getLogger(__name__)

VALIDATION_LAMBDA_ENV = "VALIDATION_LAMBDA_FUNCTION"

# Invoke budget: the function's own 8s ceiling (6.2s in-child deadline +
# fork + cold-start import of the games tree) plus network slack.
INVOKE_READ_TIMEOUT = 10
INVOKE_CONNECT_TIMEOUT = 2

# Local subprocess budget: interpreter start + games import + the 6.2s
# in-child deadline.
LOCAL_RUN_TIMEOUT = 8

# The old worker ran --concurrency=4; 4 transient interpreters is a
# comparable ceiling for the API container's mem/pids caps.
LOCAL_MAX_CONCURRENT = 4

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Deliberately outside every hint_context.classify_outcome prefix — a service
# fault is not the student's doing, so it classifies as unknown, exactly like
# the old await_validation_result generic branch.
_STUDENT_ERROR_VALIDATION = (
    "Error during validation: the execution service failed."
)

_lambda_client = None
_local_semaphore = asyncio.Semaphore(LOCAL_MAX_CONCURRENT)
_warned_local_in_prod = False


class _LambdaFunctionError(Exception):
    """The function ran but reported an error (timeout, OOM, handler bug)."""


def _get_lambda_client():
    """Module-cached boto3 Lambda client.

    boto3 is imported lazily so the executor/handler zip and the local
    subprocess path never need it. Config is deliberate: zero retries (a
    retry would re-run agent code) and a read timeout under the router's
    patience (botocore's default is 60s).
    """
    global _lambda_client
    if _lambda_client is None:
        import boto3
        from botocore.config import Config

        _lambda_client = boto3.client(
            "lambda",
            region_name=os.environ.get("AWS_REGION", "ap-southeast-2"),
            config=Config(
                retries={"max_attempts": 0},
                read_timeout=INVOKE_READ_TIMEOUT,
                connect_timeout=INVOKE_CONNECT_TIMEOUT,
            ),
        )
    return _lambda_client


def _invoke_lambda_sync(function_name: str, event: Dict[str, Any]) -> Dict[str, Any]:
    response = _get_lambda_client().invoke(
        FunctionName=function_name,
        Payload=json.dumps(event).encode(),
    )
    payload = response["Payload"].read()
    if response.get("FunctionError"):
        try:
            message = json.loads(payload).get("errorMessage", "")
        except ValueError:
            message = ""
        raise _LambdaFunctionError(message)
    return json.loads(payload)


def _is_lambda_timeout(exc: Exception) -> bool:
    """Failures that mean "the run was killed", not "the service is broken"."""
    if isinstance(exc, _LambdaFunctionError):
        text = str(exc)
        return "Task timed out" in text or "Runtime exited" in text
    return False


def _scrubbed_env() -> Dict[str, str]:
    """Environment for the local runner: interpreter essentials only.

    The subprocess (not a fork) plus this scrub is what keeps SECRET_KEY,
    DATABASE_URL, and AWS creds away from agent code in local mode. The
    dotenv re-injection hole is closed separately by local_run.py's
    backend.config stub.
    """
    env = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")}
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        env["PYTHONPATH"] = pythonpath
    return env


def _run_local_sync(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run the event through local_run.py; None means "no usable result"."""
    process = subprocess.Popen(
        [sys.executable, "-m", "backend.validation_lambda.local_run"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_scrubbed_env(),
        cwd=str(_REPO_ROOT),
        start_new_session=True,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(json.dumps(event), timeout=LOCAL_RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        # start_new_session makes the runner a group leader; kill the whole
        # group so nothing agent code forked survives inside the container.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        process.wait()
        return None
    if process.returncode != 0:
        logger.error(
            "local validation runner exited %s: %s", process.returncode, stderr[-2000:]
        )
        return None
    try:
        return json.loads(stdout)
    except ValueError:
        logger.error("local validation runner produced unparsable output")
        return None


async def _dispatch(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run the event via Lambda or the local subprocess.

    Returns the raw envelope dict, None for "killed / no result" (caller maps
    to the timeout envelope), or raises for service faults (caller maps to
    the generic error envelope).
    """
    function_name = os.environ.get(VALIDATION_LAMBDA_ENV)
    if function_name:
        try:
            return await asyncio.to_thread(_invoke_lambda_sync, function_name, event)
        except Exception as e:  # noqa: BLE001 - mapped below, never re-raised raw
            if _is_lambda_timeout(e):
                return None
            from botocore.exceptions import ConnectTimeoutError, ReadTimeoutError

            if isinstance(e, (ReadTimeoutError, ConnectTimeoutError)):
                logger.error("validation Lambda invoke timed out: %s", e)
                return None
            raise

    global _warned_local_in_prod
    if not _warned_local_in_prod and os.environ.get("DB_ENVIRONMENT") == "production":
        _warned_local_in_prod = True
        logger.warning(
            "%s is unset — agent validation is running as local subprocesses "
            "inside the API container (emergency degraded mode)",
            VALIDATION_LAMBDA_ENV,
        )
    async with _local_semaphore:
        return await asyncio.to_thread(_run_local_sync, event)


async def run_validation_fallback(
    code: str, game_name: str, team_name: str
) -> Dict[str, Any]:
    """Run a validation server-side; always returns a normalized 7-key envelope."""
    event = {
        "kind": "validation",
        "code": code,
        "game_name": game_name,
        "team_name": team_name,
    }
    try:
        raw = await _dispatch(event)
    except Exception:  # noqa: BLE001 - any service fault becomes a clean error
        logger.exception("server-side validation failed")
        return normalize_result(
            {"status": "error", "message": _STUDENT_ERROR_VALIDATION}
        )
    if raw is None:
        return timeout_validation_result()
    return normalize_result(raw)
