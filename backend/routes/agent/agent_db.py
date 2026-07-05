import os

from redis import Redis
from sqlmodel import Session, select

from backend.database.db_models import League
from backend.tasks.celery_app import broker_url

# Env-overridable default; read at call time so tests can monkeypatch it and
# exercise the rate-limited branch without ten real simulation runs.
SIMULATIONS_PER_MINUTE = int(os.environ.get("AGENT_SIMULATIONS_PER_MINUTE", "10"))
RATE_WINDOW_SECONDS = 60

_redis: Redis | None = None


def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(broker_url)
    return _redis


def get_league_by_id(session: Session, league_id: int) -> League | None:
    return session.exec(select(League).where(League.id == league_id)).one_or_none()


class SimulationLimitExceededError(Exception):
    """Raised when simulation rate limit is exceeded"""

    pass


def allow_simulation(team_id: int, limit: int | None = None) -> bool:
    """Fixed-window rate limit on agent simulation requests.

    Counted in valkey rather than the DB: /agent/simulate persists nothing, so
    a row count (the allow_submission approach) has nothing to count, and the
    API runs several gunicorn workers, so an in-process counter would multiply
    the limit. EXPIRE NX starts the window on the first request and heals a
    counter that lost its TTL.
    """
    if limit is None:
        limit = SIMULATIONS_PER_MINUTE
    key = f"agent-sim-rate:{team_id}"
    with _get_redis().pipeline() as pipe:
        pipe.incr(key)
        pipe.expire(key, RATE_WINDOW_SECONDS, nx=True)
        count, _ = pipe.execute()
    if count > limit:
        raise SimulationLimitExceededError(
            f"Rate limit exceeded: you can run at most {limit} simulations "
            f"per minute."
        )
    return True
