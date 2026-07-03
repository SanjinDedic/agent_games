"""Scheduled database maintenance.

Run inside the api container by the daily-maintenance GitHub workflow:
    python -m backend.database.maintenance
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, delete, select

from backend.database.db_models import (
    Institution,
    Submission,
    SubmissionMetadata,
    Team,
    TeamType,
)
from backend.database.db_session import get_db_engine

logger = logging.getLogger(__name__)

CLEANUP_INSTITUTIONS = ["Admin Institution", "Demo Institution"]


def _delete_submissions_older_than(session: Session, team_ids, cutoff) -> int:
    """Delete submission attempts for the given team-id subquery older than
    `cutoff`. Returns the number of attempts deleted. Does not commit."""
    old_meta_ids = [
        m.id
        for m in session.exec(
            select(SubmissionMetadata)
            .where(SubmissionMetadata.team_id.in_(team_ids))
            .where(SubmissionMetadata.timestamp < cutoff)
        ).all()
    ]

    # Code rows go first: Submission carries the FK to SubmissionMetadata
    if old_meta_ids:
        session.exec(
            delete(Submission).where(Submission.metadata_id.in_(old_meta_ids))
        )
        session.exec(
            delete(SubmissionMetadata).where(SubmissionMetadata.id.in_(old_meta_ids))
        )
    return len(old_meta_ids)


def cleanup_institution_submissions(
    session: Session,
    institution_names: list[str] = CLEANUP_INSTITUTIONS,
    age_hours: int = 24,
) -> int:
    """Delete submission attempts older than `age_hours` from teams belonging
    to the named institutions. Returns the number of attempts deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=age_hours)

    team_ids = select(Team.id).where(
        Team.institution_id.in_(
            select(Institution.id).where(Institution.name.in_(institution_names))
        )
    )
    count = _delete_submissions_older_than(session, team_ids, cutoff)
    session.commit()
    logger.info(
        f"Deleted {count} submission attempt(s) older than "
        f"{age_hours}h from {', '.join(institution_names)}"
    )
    return count


def cleanup_agent_submissions(session: Session, age_days: int = 7) -> int:
    """Delete submission attempts older than `age_days` from agent teams
    (TeamType.AGENT — teams driven via the agent router / API keys).
    Returns the number of attempts deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=age_days)

    team_ids = select(Team.id).where(Team.team_type == TeamType.AGENT)
    count = _delete_submissions_older_than(session, team_ids, cutoff)
    session.commit()
    logger.info(
        f"Deleted {count} agent-team submission attempt(s) older than {age_days}d"
    )
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with Session(get_db_engine()) as session:
        institution_deleted = cleanup_institution_submissions(session)
        agent_deleted = cleanup_agent_submissions(session)
    print(
        f"Maintenance done: {institution_deleted} institution + "
        f"{agent_deleted} agent submission attempt(s) deleted"
    )
