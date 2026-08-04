"""Counters for which environment ran submitted code: Pyodide vs Lambda.

Every game and exercise submission passes through one of four endpoints —
/user/submit-agent and /tutorial/submit-exercise (server path, Lambda or its
local-subprocess degraded mode) or /user/submit-agent-result and
/tutorial/submit-exercise-result (the browser already ran the code via
Pyodide). Each calls record_code_env_call after its rate limit, so spam can't
inflate the counters and a 429'd attempt isn't counted.

Unlike the Valkey fallback telemetry (pyodide_support.py), these counters are
durable and keyed by user: submission rows are routinely purged (demo
cleanup), so the counts live in their own FK-free table that survives every
cleanup path. The stored granularity is the ceiling by design — one row per
(user, kind, environment), nothing per-submission.
"""

import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, func, select

from backend.database.db_models import CodeEnvUsage
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)

KIND_GAME = "game"
KIND_EXERCISE = "exercise"
ENV_PYODIDE = "pyodide"
ENV_LAMBDA = "lambda"


def record_code_env_call(
    session: Session, user_identifier: str, kind: str, environment: str
) -> None:
    """Count one submission for (user, kind, environment).

    A single upsert so concurrent submissions can't lose increments. Fails
    open like the fallback telemetry — the submission itself must not suffer
    for a counter — but rolls back first so a failure can't poison the
    request's session.
    """
    table = CodeEnvUsage.__table__
    statement = (
        pg_insert(table)
        .values(
            user_identifier=user_identifier,
            kind=kind,
            environment=environment,
            call_count=1,
            last_used=utc_now(),
        )
        .on_conflict_do_update(
            index_elements=["user_identifier", "kind", "environment"],
            set_={"call_count": table.c.call_count + 1, "last_used": utc_now()},
        )
    )
    try:
        session.execute(statement)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception(
            "code-env counter unavailable (user=%s kind=%s env=%s); "
            "submission continues",
            user_identifier,
            kind,
            environment,
        )


def get_code_env_stats(session: Session) -> dict:
    """Users and call totals per (kind, environment), plus per-environment
    totals where a user active in both kinds counts once."""
    cells = session.exec(
        select(
            CodeEnvUsage.kind,
            CodeEnvUsage.environment,
            func.count(CodeEnvUsage.id),
            func.coalesce(func.sum(CodeEnvUsage.call_count), 0),
        ).group_by(CodeEnvUsage.kind, CodeEnvUsage.environment)
    ).all()
    totals = session.exec(
        select(
            CodeEnvUsage.environment,
            func.count(func.distinct(CodeEnvUsage.user_identifier)),
            func.coalesce(func.sum(CodeEnvUsage.call_count), 0),
        ).group_by(CodeEnvUsage.environment)
    ).all()
    return {
        "stats": [
            {"kind": kind, "environment": env, "users": users, "calls": calls}
            for kind, env, users, calls in cells
        ],
        "totals": {
            env: {"users": users, "calls": calls} for env, users, calls in totals
        },
    }
