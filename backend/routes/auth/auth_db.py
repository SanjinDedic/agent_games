from datetime import timedelta

from sqlmodel import Session, create_engine, select

from backend.database.db_config import get_database_url
from backend.database.db_models import Admin, Team
from backend.routes.auth.auth_core import create_access_token


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid"""

    pass


def get_db():
    """Database session dependency"""
    engine = create_engine(get_database_url())
    with Session(engine) as session:
        yield session


def get_team_token(session: Session, team_name: str, team_password: str):
    """Get authentication token for team login"""
    team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()

    if not team:
        raise InvalidCredentialsError(f"Team '{team_name}' not found")

    if not team.verify_password(team_password):
        raise InvalidCredentialsError("Invalid team password")

    access_token_expires = timedelta(minutes=20)
    access_token = create_access_token(
        data={"sub": team_name, "role": "student"}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


def get_admin_token(session: Session, username: str, password: str):
    """Get authentication token for admin login"""
    admin = session.exec(select(Admin).where(Admin.username == username)).one_or_none()

    if not admin or not admin.verify_password(password):
        raise InvalidCredentialsError("Invalid credentials")

    access_token_expires = timedelta(minutes=20)
    access_token = create_access_token(
        data={"sub": "admin", "role": "admin"}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}
