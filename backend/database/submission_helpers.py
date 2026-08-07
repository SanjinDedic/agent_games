from typing import Sequence

from sqlmodel import Session, delete, select, update

from backend.database.db_models import (
    AgentAPIKey,
    SimulationResultItem,
    Submission,
    SubmissionMetadata,
    SupportTicket,
)


def delete_submissions_for_teams(session: Session, team_ids: Sequence[int]) -> None:
    """Delete all submission rows for the given teams.

    Code rows must go first: Submission carries the FK to SubmissionMetadata.
    Does not commit; the caller owns the transaction.
    """
    if not team_ids:
        return
    meta_ids = select(SubmissionMetadata.id).where(
        SubmissionMetadata.team_id.in_(team_ids)
    )
    session.exec(delete(Submission).where(Submission.metadata_id.in_(meta_ids)))
    session.exec(
        delete(SubmissionMetadata).where(SubmissionMetadata.team_id.in_(team_ids))
    )


def delete_team_children(session: Session, team_ids: Sequence[int]) -> None:
    """Clear every row that references the given teams, so the Team rows can go.

    Every path that deletes a Team must call this first. None of these FKs are
    ON DELETE CASCADE, so a single leftover child row turns the delete into a
    500. When a new table gains a team_id, add it here rather than to the
    individual delete paths.

    Support tickets are detached instead of deleted: they own S3 attachments
    that only the institution purge knows how to clean up, and support history
    outlives the team. The institution purge deletes its tickets before calling
    this, so the detach is a no-op there.

    Does not commit; the caller owns the transaction.
    """
    if not team_ids:
        return
    delete_submissions_for_teams(session, team_ids)
    session.exec(
        delete(SimulationResultItem).where(SimulationResultItem.team_id.in_(team_ids))
    )
    session.exec(delete(AgentAPIKey).where(AgentAPIKey.team_id.in_(team_ids)))
    session.exec(
        update(SupportTicket)
        .where(SupportTicket.team_id.in_(team_ids))
        .values(team_id=None)
    )
