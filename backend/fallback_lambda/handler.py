"""Event dispatch for the exercise-fallback Lambda (and the local runner).

``handle`` is pure so the Lambda entry point and the local subprocess CLI
(local_run.py) share one code path. Events:

    {"kind": "exercise", "code": ..., "entry_function": ..., "test_code": ...}
    {"kind": "snippet", "code": ...}

The response is always the full normalized envelope — 7 keys for exercises,
5 for snippets — never an exception: the API client treats the payload as
the finished result.
"""

import logging
import time
from typing import Any, Dict

from backend.fallback_lambda.executor import (
    normalize_result,
    run_exercise_isolated,
    run_snippet_isolated,
)

logger = logging.getLogger(__name__)


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


def lambda_handler(event, context):
    """AWS Lambda entry point (handler string:
    backend.fallback_lambda.handler.lambda_handler)."""
    t0 = time.perf_counter()
    result = handle(event)
    # Log kind + timing only — never student code or its output.
    logger.info(
        "kind=%s status=%s wall_ms=%.0f",
        event.get("kind"),
        result.get("status"),
        (time.perf_counter() - t0) * 1000,
    )
    return result
