"""Shared helpers for the team-signup endpoints (classic + school)."""

from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlmodel import Session

from backend.database.db_models import League, Team
from backend.routes.auth.auth_config import (
    AUSTRALIA_SYDNEY_TZ,
    TEAM_TOKEN_EXPIRY_MINUTES,
    create_access_token,
)
from backend.routes.user.user_db import get_league_by_signup_token


def resolve_active_league_by_token(
    session: Session, signup_token: str
) -> Tuple[Optional[League], Optional[str]]:
    """Resolve a league from a signup token and check it's still open.

    Returns (league, None) on success or (None, error_message) if the token
    doesn't match or the league has expired.
    """
    league = get_league_by_signup_token(session, signup_token)
    if not league:
        return None, "Invalid signup link or league not found"

    now = datetime.now(AUSTRALIA_SYDNEY_TZ)
    expiry_date = league.expiry_date
    if expiry_date.tzinfo is None:
        expiry_date = AUSTRALIA_SYDNEY_TZ.localize(expiry_date)
    if expiry_date < now:
        return (
            None,
            "This league has expired and is no longer accepting new teams",
        )

    return league, None


def team_signup_success_data(team: Team, league: League) -> dict:
    """The response data shape shared by both signup endpoints."""
    access_token = create_access_token(
        data={"sub": team.name, "role": "student"},
        expires_delta=timedelta(minutes=TEAM_TOKEN_EXPIRY_MINUTES),
    )
    return {
        "team_id": team.id,
        "team_name": team.name,
        "league_id": league.id,
        "league_name": league.name,
        "access_token": access_token,
        "token_type": "bearer",
    }
