from datetime import datetime, timedelta

import pytz
import sqlmodel
from sqlmodel import Session, select

from backend.database.db_models import League, SimulationResult

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


def get_league_by_id(session: sqlmodel.Session, league_id: int) -> sqlmodel.Session:
    return session.exec(select(League).where(League.id == league_id)).one_or_none()


class SimulationLimitExceededError(Exception):
    """Raised when simulation rate limit is exceeded"""

    pass


def allow_simulation(session: Session, team_id: int) -> bool:
    """Check if team is allowed to run simulation (rate limiting)"""
    one_minute_ago = datetime.now(AUSTRALIA_SYDNEY_TZ) - timedelta(minutes=1)
    recent_sims = session.exec(
        select(SimulationResult)
        .where(SimulationResult.id == team_id)
        .where(SimulationResult.timestamp >= one_minute_ago)
    ).all()
    if len(recent_sims) >= 10:
        raise SimulationLimitExceededError(
            "You can only run 10 simulations per minute."
        )
    return True
