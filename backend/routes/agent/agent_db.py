from datetime import datetime, timedelta

import pytz
import sqlmodel
from sqlmodel import Session, select

from backend.database.db_models import League, SimulationResult, Team

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


def get_league_by_id(session: sqlmodel.Session, league_id: int) -> sqlmodel.Session:
    return session.exec(select(League).where(League.id == league_id)).one_or_none()


def get_team_id_by_name(session: sqlmodel.Session, team_name: str) -> sqlmodel.Session:
    return session.exec(select(Team).where(Team.name == team_name)).one_or_none()


class SimulationLimitExceededError(Exception):
    """Raised when simulation rate limit is exceeded"""

    pass


def allow_simulation(session: Session, team_id: int) -> bool:
    print("Here is the team_id", team_id, "we are in allow_simulation")
    """Check if team is allowed to run simulation (rate limiting)"""
    one_minute_ago = datetime.now(AUSTRALIA_SYDNEY_TZ) - timedelta(minutes=1)
    # We'll use the existing SimulationResult table but only count recent ones
    recent_sims = session.exec(
        select(SimulationResult)
        .where(SimulationResult.id == team_id)
        .where(SimulationResult.timestamp >= one_minute_ago)
    ).all()
    print("Here is the recent_sims", recent_sims)
    if len(recent_sims) >= 10:  # Allow 10 per minute
        raise SimulationLimitExceededError(
            "You can only run 10 simulations per minute."
        )
    return True
