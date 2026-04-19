import logging
import re

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from backend.database.db_models import League, Team, TeamType

logger = logging.getLogger(__name__)
MAX_COLLISION_RETRIES = 10


def sanitize_school_name(s: str) -> str:
    """Strip all non-alphanumerics; preserve casing.

    'Willetton SHS!' -> 'WillettonSHS'. Accents/non-ASCII are stripped (e.g.
    'École' -> 'cole'); callers that need Unicode should pre-normalize.
    """
    return re.sub(r"[^A-Za-z0-9]", "", s or "")


def next_available_team_name(session: Session, sanitized: str, start: int = 1) -> str:
    """Find the lowest N >= start such that f'{sanitized}{N}' is globally unused
    as Team.name.

    Counter scope: Team.name is globally unique, so this is effectively a
    "next globally-unused N". In practice it matches per-league counting;
    when the same sanitized school appears across leagues, N skips past
    whichever numbers are already taken.
    """
    if not sanitized:
        raise ValueError("Sanitized school name is empty; cannot derive team name")

    existing = session.exec(
        select(Team.name).where(Team.name.like(f"{sanitized}%"))
    ).all()

    used = set()
    for name in existing:
        suffix = name[len(sanitized):]
        if suffix.isdigit():
            used.add(int(suffix))

    n = start
    while n in used:
        n += 1
    return f"{sanitized}{n}"


def create_school_team(
    session: Session, league_id: int, school_name: str, password: str
) -> Team:
    """Create a team for a school league with sanitized name + counter.

    Race-safe: on IntegrityError from the unique-name constraint, bump the
    counter past the collision and retry up to MAX_COLLISION_RETRIES times.
    """
    league = session.get(League, league_id)
    if not league:
        raise ValueError(f"League {league_id} not found")

    sanitized = sanitize_school_name(school_name)
    if not sanitized:
        raise ValueError(
            f"School name '{school_name}' contains no alphanumerics"
        )

    start = 1
    for attempt in range(MAX_COLLISION_RETRIES):
        candidate = next_available_team_name(session, sanitized, start=start)
        try:
            team = Team(
                name=candidate,
                school_name=school_name,
                league_id=league_id,
                institution_id=league.institution_id,
                team_type=TeamType.STUDENT,
            )
            team.set_password(password)
            session.add(team)
            session.commit()
            session.refresh(team)
            return team
        except IntegrityError:
            session.rollback()
            logger.warning(
                "Race on team name %s; retrying (attempt %d)", candidate, attempt + 1
            )
            try:
                start = int(candidate[len(sanitized):]) + 1
            except ValueError:
                start += 1
            continue
    raise RuntimeError(
        f"Failed to create school team after {MAX_COLLISION_RETRIES} retries"
    )
