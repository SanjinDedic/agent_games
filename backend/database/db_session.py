from sqlmodel import Session, create_engine

from backend.database.db_config import get_database_url

_engine = None


def get_db_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_database_url())
    return _engine


def get_db():
    """Database session dependency"""
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
