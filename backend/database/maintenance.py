"""Scheduled database maintenance.

Run inside the api container:
    python -m backend.database.maintenance

Only agent-team submissions are pruned. The other sweep used to target two
institutions by name; demo mode and institutions are both gone, and a
single-tenant install has no throwaway tenant whose submissions are disposable,
so a student's history is kept until their team is deleted.
"""

import logging
from datetime import timedelta

from sqlmodel import Session, delete, select

from backend.database.db_models import (
    Submission,
    SubmissionMetadata,
    Team,
    TeamType,
)
from backend.database.db_session import get_db_engine
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)


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


def cleanup_agent_submissions(session: Session, age_days: int = 7) -> int:
    """Delete submission attempts older than `age_days` from agent teams
    (TeamType.AGENT — teams driven via the agent router / API keys).
    Returns the number of attempts deleted."""
    cutoff = utc_now() - timedelta(days=age_days)

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
        agent_deleted = cleanup_agent_submissions(session)
    print(f"Maintenance done: {agent_deleted} agent submission attempt(s) deleted")
