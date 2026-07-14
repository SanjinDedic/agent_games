import os

from sqlmodel import Session, create_engine

from backend.database.db_config import get_database_url

_engine = None


def get_db_engine():
    global _engine
    if _engine is None:
        # Production is a DigitalOcean managed cluster, not a postgres container
        # on the loopback, so the pool is self-healing:
        #   pool_pre_ping — the managed proxy drops idle connections (and
        #     failover swaps the backend); without it the first query on a stale
        #     connection raises instead of transparently reconnecting.
        #   pool_recycle — never hand out a connection the server may have already
        #     timed out. 300s sits under the managed idle cutoff.
        # These are cheap everywhere, so they stay on for dev/test too.
        kwargs = dict(pool_pre_ping=True, pool_recycle=300)

        # The smallest managed plan allows ~22 client connections for the whole
        # cluster, shared by the gunicorn workers and every forked Celery child.
        # SQLAlchemy's default 5+10 per process can exhaust that, so prod sets
        # DB_POOL_SIZE/DB_MAX_OVERFLOW small (see config/deploy.yml). Unset (dev
        # and the test suite on a local cluster with no such cap) keeps the
        # generous defaults — a tiny pool there just serializes tests.
        if os.environ.get("DB_POOL_SIZE"):
            kwargs["pool_size"] = int(os.environ["DB_POOL_SIZE"])
        if os.environ.get("DB_MAX_OVERFLOW"):
            kwargs["max_overflow"] = int(os.environ["DB_MAX_OVERFLOW"])

        _engine = create_engine(get_database_url(), **kwargs)
    return _engine


def get_db():
    """Database session dependency"""
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
