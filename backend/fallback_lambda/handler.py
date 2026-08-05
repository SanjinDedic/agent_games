"""Event dispatch for the exercise-fallback Lambda (and the local runner).

``handle`` is pure so the Lambda entry point and the local subprocess CLI
(local_run.py) share one code path. Events:

    {"kind": "exercise", "code": ..., "entry_function": ..., "test_code": ...}
    {"kind": "snippet", "code": ...}

The response is always the full normalized envelope — 7 keys for exercises,
5 for snippets — never an exception: the API client treats the payload as
the finished result.

``lambda_handler`` additionally accepts Function URL events (detected by
``requestContext``): the browser calls the URL directly with an execution
token minted by the API (exec_token.py verifies it against
``EXEC_JWT_SECRET``), and the same envelope comes back as the HTTP body.
Preflight/CORS is handled by the Function URL's own CORS config, never here.
"""

import base64
import json
import logging
import os
import time
from typing import Any, Dict, Optional

from backend.fallback_lambda import exec_token
from backend.fallback_lambda.executor import (
    normalize_result,
    run_exercise_isolated,
    run_snippet_isolated,
)

logger = logging.getLogger(__name__)

# Generous ceilings for hand-typed student code; anything bigger is abuse,
# not an exercise. Checked before the fork so oversized payloads cost nothing.
MAX_CODE_CHARS = 100_000
MAX_BODY_BYTES = 256_000


def handle(event: Dict[str, Any]) -> Dict[str, Any]:
    kind = event.get("kind")
    if kind == "exercise":
        return run_exercise_isolated(
            event["code"], event["entry_function"], event.get("test_code")
        )
    if kind == "snippet":
        return run_snippet_isolated(event["code"])
    return normalize_result(
        {"status": "error", "message": f"Unknown event kind: {kind!r}"}
    )


def _http_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_http_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Decoded JSON body of a Function URL event, or None if malformed."""
    body = event.get("body")
    if not isinstance(body, str) or len(body) > MAX_BODY_BYTES:
        return None
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode()
        except (ValueError, UnicodeDecodeError):
            return None
    try:
        payload = json.loads(body)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _handle_http(event: Dict[str, Any]) -> Dict[str, Any]:
    """Function URL request → verified, size-capped dispatch to handle()."""
    method = (
        event.get("requestContext", {}).get("http", {}).get("method", "")
    )
    if method != "POST":
        return _http_response(405, {"detail": "POST only"})

    secret = os.environ.get("EXEC_JWT_SECRET", "")
    if not secret:
        # Fail closed: a misdeployed function must not become an open runner.
        logger.error("EXEC_JWT_SECRET is not set — rejecting request")
        return _http_response(401, {"detail": "Execution token invalid"})
    auth_header = event.get("headers", {}).get("authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    claims = exec_token.verify(token, secret)
    if claims is None:
        return _http_response(401, {"detail": "Execution token invalid"})

    payload = _parse_http_body(event)
    if payload is None:
        return _http_response(400, {"detail": "Malformed JSON body"})
    kind = payload.get("kind")
    if kind not in ("exercise", "snippet"):
        return _http_response(400, {"detail": f"Unknown event kind: {kind!r}"})
    code = payload.get("code")
    test_code = payload.get("test_code")
    if test_code is None:
        test_code = ""
    entry_function = payload.get("entry_function")
    if (
        not isinstance(code, str)
        or not isinstance(test_code, str)
        or (kind == "exercise" and not isinstance(entry_function, str))
    ):
        return _http_response(400, {"detail": "Malformed JSON body"})
    if len(code) > MAX_CODE_CHARS or len(test_code) > MAX_CODE_CHARS:
        return _http_response(413, {"detail": "Code too large"})

    result = handle(payload)
    return _http_response(200, result)


def lambda_handler(event, context):
    """AWS Lambda entry point (handler string:
    backend.fallback_lambda.handler.lambda_handler).

    Two event shapes: Function URL requests (direct browser calls, detected
    by ``requestContext``) and plain invoke payloads (the API's boto3 path,
    unchanged).
    """
    t0 = time.perf_counter()
    if "requestContext" in event:
        response = _handle_http(event)
        # Log status + timing only — never student code or its output.
        logger.info(
            "http status=%s wall_ms=%.0f",
            response.get("statusCode"),
            (time.perf_counter() - t0) * 1000,
        )
        return response
    result = handle(event)
    # Log kind + timing only — never student code or its output.
    logger.info(
        "kind=%s status=%s wall_ms=%.0f",
        event.get("kind"),
        result.get("status"),
        (time.perf_counter() - t0) * 1000,
    )
    return result
