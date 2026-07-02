from typing import Sequence

from sqlmodel import Session, delete, select

from backend.database.db_models import Submission, SubmissionMetadata


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
