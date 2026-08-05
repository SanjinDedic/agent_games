"""Server-side support for in-browser (Pyodide) exercise runs.

The browser executes exercises locally via
frontend/src/pyodide/exercise_harness.py and submits the finished envelope to
/tutorial/submit-exercise-result; when Pyodide cannot run at all, the browser
calls the fallback Lambda's Function URL directly (the server never executes
the code) and the persisted envelope carries
execution_source="pyodide_fallback". Every fallback is logged and counted in
Valkey so the migration can prove when the exercise fallback path
(backend/lambda_fallback/exercise_snippet/) has become dead weight and can be deleted.
"""

import logging
from datetime import timedelta
from typing import Optional

import redis

from backend.config import VALKEY_URL
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)

# The row keys the frontend renders (ExerciseResults.jsx) and the fallback
# runner emits (backend/lambda_fallback/exercise_snippet/executor.py _append_row); anything else a
# client sends is dropped before storage.
ROW_KEYS = ("name", "call", "expected", "actual", "passed", "error")

FALLBACK_KEY_TTL = int(timedelta(days=30).total_seconds())

_valkey_client: Optional[redis.Redis] = None


def _get_valkey_client() -> redis.Redis:
    global _valkey_client
    if _valkey_client is None:
        _valkey_client = redis.Redis.from_url(VALKEY_URL, decode_responses=True)
    return _valkey_client


def normalize_client_rows(test_results: list, source: str) -> list:
    """Rebuild client-supplied result rows, keeping only the contract keys.

    Extra keys are dropped, ``passed`` is coerced to bool, and ``call`` is
    forced to None (the worker never sets it either); each row is then
    stamped with the execution ``source`` ("pyodide" for in-browser runs,
    "celery_fallback" for browser submissions that fell back). The stamp
    lives inside the stored test_results JSON, so no schema change is needed
    and every consumer that enumerates rows ignores it.
    """
    rows = []
    for row in test_results:
        if not isinstance(row, dict):
            continue
        clean = {key: row.get(key) for key in ROW_KEYS}
        clean["passed"] = bool(clean["passed"])
        clean["call"] = None
        clean["source"] = source
        rows.append(clean)
    return rows


def record_pyodide_fallback(team_id: Optional[int], reason: str) -> None:
    """Count one browser-to-server fallback.

    Shared by exercise submissions, lesson snippet runs, and agent
    validation — snippet fallbacks arrive with a "snippet:" reason prefix
    (lesson_router) and validation ones with "validation:" (user_router), so
    one counter answers for all three. The warning line is the durable
    per-occurrence record; the Valkey counters give the aggregate view for
    /diagnostics/pyodide-fallbacks. Fails open on a Valkey error — the
    submission itself must not suffer for telemetry.
    """
    logger.warning("Pyodide fallback: team=%s reason=%s", team_id, reason)
    day = utc_now().strftime("%Y-%m-%d")
    try:
        client = _get_valkey_client()
        client.incr(f"pyodide-fallback:count:{day}")
        client.expire(f"pyodide-fallback:count:{day}", FALLBACK_KEY_TTL)
        client.hincrby(f"pyodide-fallback:reasons:{day}", reason, 1)
        client.expire(f"pyodide-fallback:reasons:{day}", FALLBACK_KEY_TTL)
    except redis.RedisError:
        logger.warning("Pyodide fallback counter unavailable; logged only")


def get_pyodide_fallback_stats(days: int = 14) -> dict:
    """Per-day fallback counts and reasons, newest first, zero days omitted."""
    try:
        client = _get_valkey_client()
        day_stats = []
        total = 0
        today = utc_now().date()
        for offset in range(days):
            day = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
            count = int(client.get(f"pyodide-fallback:count:{day}") or 0)
            if not count:
                continue
            reasons = {
                key: int(value)
                for key, value in client.hgetall(
                    f"pyodide-fallback:reasons:{day}"
                ).items()
            }
            day_stats.append({"date": day, "count": count, "reasons": reasons})
            total += count
        return {"days": day_stats, "total": total}
    except redis.RedisError as e:
        logger.warning("Pyodide fallback stats unavailable: %s", e)
        return {"days": [], "total": 0, "error": str(e)}
