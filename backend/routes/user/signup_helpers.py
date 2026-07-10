"""Shared helpers for the team-signup endpoints (classic + school)."""

from sqlmodel import Session

from backend.database.db_models import League, Team
from backend.routes.auth.auth_db import mint_team_token
from backend.routes.user.user_db import LeagueExpiredError, get_league_by_signup_token
from backend.time_utils import ensure_utc, utc_now


def resolve_active_league_by_token(session: Session, signup_token: str) -> League:
    """Resolve a league from a signup token and check it's still open.

    Raises LeagueNotFoundError (HTTP 404) for an unknown token and
    LeagueExpiredError (HTTP 410) for a league past its expiry date.
    """
    league = get_league_by_signup_token(session, signup_token)

    if ensure_utc(league.expiry_date) < utc_now():
        raise LeagueExpiredError(
            "This league has expired and is no longer accepting new teams"
        )

    return league


def team_signup_success_data(team: Team, league: League) -> dict:
    """The response data shape shared by both signup endpoints."""
    return {
        "team_id": team.id,
        "team_name": team.name,
        "league_id": league.id,
        "league_name": league.name,
        "access_token": mint_team_token(team),
        "token_type": "bearer",
    }
