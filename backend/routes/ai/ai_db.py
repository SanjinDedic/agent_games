import logging
from datetime import UTC, datetime
from typing import Dict, List, Optional

from sqlmodel import Session, select

from backend.database.db_models import AIProviderKey, Submission, Team

logger = logging.getLogger(__name__)


def mask_key(key: Optional[str]) -> str:
    """Mask an API key for safe display. Shows first 4 and last 4 characters."""
    if not key:
        return ""
    if len(key) > 8:
        return f"{key[:4]}****{key[-4:]}"
    return "****"


def get_api_keys(session: Session) -> Dict:
    """Retrieve all AI provider keys, masked."""
    openai_row = session.exec(
        select(AIProviderKey).where(AIProviderKey.provider == "openai")
    ).first()
    return {
        "openai_api_key": mask_key(openai_row.api_key if openai_row else None),
    }


def update_api_key(session: Session, provider: str, api_key: str) -> None:
    """Upsert an AI provider key."""
    existing = session.exec(
        select(AIProviderKey).where(AIProviderKey.provider == provider)
    ).first()
    if existing:
        existing.api_key = api_key
        existing.updated_at = datetime.now(UTC)
        session.add(existing)
    else:
        new_key = AIProviderKey(
            provider=provider,
            api_key=api_key,
        )
        session.add(new_key)
    session.commit()


def get_stored_key(session: Session, provider: str) -> Optional[str]:
    """Get the raw (unmasked) key for a provider, or None."""
    row = session.exec(
        select(AIProviderKey).where(AIProviderKey.provider == provider)
    ).first()
    return row.api_key if row else None


# --- Plagiarism assessment helpers ---


def get_team_submissions_ordered(
    session: Session, team_id: int
) -> List[Submission]:
    """Return all submissions for a team in ascending timestamp order."""
    return list(
        session.exec(
            select(Submission)
            .where(Submission.team_id == team_id)
            .order_by(Submission.timestamp.asc())
        ).all()
    )


def get_team_in_league(
    session: Session, team_name: str, league_id: int
) -> Optional[Team]:
    """Look up a team by name; return None if not found or not in that league.

    Team names are globally unique (see db_models.Team), so looking up by name
    alone is unambiguous — but we still enforce the league membership as an
    authorization guard, so a caller can only assess teams inside a league they
    legitimately have access to.
    """
    team = session.exec(select(Team).where(Team.name == team_name)).first()
    if not team or team.league_id != league_id:
        return None
    return team
