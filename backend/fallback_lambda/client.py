"""API-side client for the exercise/snippet server fallback.

The only module the routes import. Two modes, switched solely on whether
EXERCISE_LAMBDA_FUNCTION is set (never on credential presence — dev's .env
carries MinIO creds that must not flip this switch):

- **Lambda mode** (env set, production): boto3 ``invoke`` of the function
  deployed from this folder (deploy.sh). Retries are OFF — a retry re-runs
  student code — and the read timeout undercuts the old 6s Celery patience.
- **Local mode** (env unset, dev/CI default): a fresh ``sys.executable``
  subprocess running local_run.py with a scrubbed environment, bounded by a
  semaphore so a submission burst can't fork-storm the API container.

Every failure mode maps to a normalized envelope — routes never see an
exception. A run that produced no result (function timeout, OOM, dead
subprocess) collapses to the canonical timeout envelope, the same collapse
the old path made for TimeLimitExceeded/WorkerLostError.
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

from backend.fallback_lambda.executor import (
    EXERCISE_TIMEOUT_MESSAGE,
    SNIPPET_TIMEOUT_MESSAGE,
    normalize_result,
    normalize_snippet_result,
)

logger = logging.getLogger(__name__)

EXERCISE_LAMBDA_ENV = "EXERCISE_LAMBDA_FUNCTION"

# Invoke budget: 1.5s hard kill + fork + cold start fits well inside 6s (the
# old API-side Celery poll budget, kept for continuity).
INVOKE_READ_TIMEOUT = 6
INVOKE_CONNECT_TIMEOUT = 2

# Local subprocess budget: interpreter start + the 1.7s in-child deadline.
LOCAL_RUN_TIMEOUT = 5

# The old worker had 2 prefork slots and queued the rest; 4 transient
# interpreters is a comparable ceiling for the API container's mem/pids caps.
LOCAL_MAX_CONCURRENT = 4

_REPO_ROOT = Path(__file__).resolve().parents[2]

_STUDENT_ERROR_EXERCISE = "Error while running tests: the execution service failed."
_STUDENT_ERROR_SNIPPET = "Error while running your code: the execution service failed."

_lambda_client = None
_local_semaphore = asyncio.Semaphore(LOCAL_MAX_CONCURRENT)
_warned_local_in_prod = False


def timeout_exercise_result() -> Dict[str, Any]:
    """ExerciseRunResponse dict for a hard-killed (timed-out) exercise run."""
    return normalize_result(
        {"status": "error", "message": EXERCISE_TIMEOUT_MESSAGE}
    )


def timeout_snippet_result() -> Dict[str, Any]:
    """SnippetRunResponse dict for a hard-killed (timed-out) snippet run."""
    return normalize_snippet_result(
        {"status": "error", "message": SNIPPET_TIMEOUT_MESSAGE}
    )


class _LambdaFunctionError(Exception):
    """The function ran but reported an error (timeout, OOM, handler bug)."""


def _get_lambda_client():
    """Module-cached boto3 Lambda client.

    boto3 is imported lazily so the executor/handler zip and the local
    subprocess path never need it. Config is deliberate: zero retries (a
    retry would re-run student code) and a read timeout under the router's
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
    DATABASE_URL, and AWS creds away from student code in local mode.
    """
    env = {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")}
    pythonpath = os.environ.get("PYTHONPATH")
    if pythonpath:
        env["PYTHONPATH"] = pythonpath
    return env


def _run_local_sync(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run the event through local_run.py; None means "no usable result"."""
    process = subprocess.Popen(
        [sys.executable, "-m", "backend.fallback_lambda.local_run"],
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
        # group so nothing student code forked survives inside the container.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        process.wait()
        return None
    if process.returncode != 0:
        logger.error(
            "local exercise runner exited %s: %s", process.returncode, stderr[-2000:]
        )
        return None
    try:
        return json.loads(stdout)
    except ValueError:
        logger.error("local exercise runner produced unparsable output")
        return None


async def _dispatch(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run the event via Lambda or the local subprocess.

    Returns the raw envelope dict, None for "killed / no result" (caller maps
    to its timeout envelope), or raises for service faults (caller maps to
    its error envelope).
    """
    function_name = os.environ.get(EXERCISE_LAMBDA_ENV)
    if function_name:
        try:
            return await asyncio.to_thread(_invoke_lambda_sync, function_name, event)
        except Exception as e:  # noqa: BLE001 - mapped below, never re-raised raw
            if _is_lambda_timeout(e):
                return None
            from botocore.exceptions import ConnectTimeoutError, ReadTimeoutError

            if isinstance(e, (ReadTimeoutError, ConnectTimeoutError)):
                logger.error("exercise Lambda invoke timed out: %s", e)
                return None
            raise

    global _warned_local_in_prod
    if not _warned_local_in_prod and os.environ.get("DB_ENVIRONMENT") == "production":
        _warned_local_in_prod = True
        logger.warning(
            "%s is unset — exercise fallback is running as local subprocesses "
            "inside the API container (emergency degraded mode)",
            EXERCISE_LAMBDA_ENV,
        )
    async with _local_semaphore:
        return await asyncio.to_thread(_run_local_sync, event)


async def run_exercise_fallback(
    code: str, entry_function: str, test_code: Optional[str]
) -> Dict[str, Any]:
    """Run an exercise server-side; always returns a normalized 7-key envelope."""
    event = {
        "kind": "exercise",
        "code": code,
        "entry_function": entry_function,
        "test_code": test_code,
    }
    try:
        raw = await _dispatch(event)
    except Exception:  # noqa: BLE001 - any service fault becomes a clean error
        logger.exception("exercise fallback failed")
        return normalize_result(
            {"status": "error", "message": _STUDENT_ERROR_EXERCISE}
        )
    if raw is None:
        return timeout_exercise_result()
    return normalize_result(raw)


async def run_snippet_fallback(code: str) -> Dict[str, Any]:
    """Run a snippet server-side; always returns a normalized 5-key envelope."""
    event = {"kind": "snippet", "code": code}
    try:
        raw = await _dispatch(event)
    except Exception:  # noqa: BLE001 - any service fault becomes a clean error
        logger.exception("snippet fallback failed")
        return normalize_snippet_result(
            {"status": "error", "message": _STUDENT_ERROR_SNIPPET}
        )
    if raw is None:
        return timeout_snippet_result()
    return normalize_snippet_result(raw)
