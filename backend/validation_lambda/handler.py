"""Event dispatch for the validation Lambda (and the local runner).

``handle`` is pure so the Lambda entry point and the local subprocess CLI
(local_run.py) share one code path. Events:

    {"kind": "validation", "code": ..., "game_name": ..., "team_name": ...}

The response is always the full normalized 7-key ValidationResponse — never
an exception: the API client treats the payload as the finished result.
"""

import logging
import time
from typing import Any, Dict

from backend.validation_lambda.executor import (
    normalize_result,
    run_validation_isolated,
)

logger = logging.getLogger(__name__)


def handle(event: Dict[str, Any]) -> Dict[str, Any]:
    kind = event.get("kind")
    if kind == "validation":
        return run_validation_isolated(
            event["code"], event["game_name"], event["team_name"]
        )
    return normalize_result(
        {"status": "error", "message": f"Unknown event kind: {kind!r}"}
    )


def lambda_handler(event, context):
    """AWS Lambda entry point (handler string:
    backend.validation_lambda.handler.lambda_handler)."""
    t0 = time.perf_counter()
    result = handle(event)
    # Log game + timing only — never agent code or its output.
    logger.info(
        "kind=%s game=%s status=%s wall_ms=%.0f",
        event.get("kind"),
        event.get("game_name"),
        result.get("status"),
        (time.perf_counter() - t0) * 1000,
    )
    return result
