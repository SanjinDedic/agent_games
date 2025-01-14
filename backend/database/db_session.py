from config import get_database_url
from sqlmodel import Session, create_engine


def get_db_engine():
    return create_engine(get_database_url())


def get_db():
    """Database session dependency"""
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
