"""Per-tier caps on how many teams/students a paid institution can create.

The cap follows the purchased plan (InstitutionSubscription.tier); institutions
without a subscription or with an unknown tier (admin-created/legacy accounts)
are uncapped. Demo and AI-agent teams never count toward the cap.
"""

from typing import Optional

from sqlmodel import Session, func, select

from backend.database.db_models import Institution, Team, TeamType

# Matches the advertised plans: Teacher 26 students; Club & School 100 teams;
# Whole School / University 500 teams/students.
TIER_TEAM_CAPS = {
    "teacher": 26,
    "club": 100,
    "school": 500,
    "university": 500,
}


class TeamLimitExceededError(Exception):
    """Raised when an institution's plan team/student cap is reached (maps to HTTP 403)."""


def assert_team_capacity(session: Session, institution_id: Optional[int]) -> None:
    """Raise TeamLimitExceededError if the institution is at its plan's cap."""
    if institution_id is None:
        return
    institution = session.get(Institution, institution_id)
    if institution is None or institution.subscription is None:
        return
    cap = TIER_TEAM_CAPS.get(institution.subscription.tier)
    if cap is None:
        return
    count = session.exec(
        select(func.count())
        .select_from(Team)
        .where(
            Team.institution_id == institution_id,
            Team.is_demo == False,  # noqa: E712
            Team.team_type == TeamType.STUDENT,
        )
    ).one()
    if count >= cap:
        noun = "students" if institution.is_teacher else "teams"
        raise TeamLimitExceededError(
            f"Your plan allows up to {cap} {noun} and that limit has been "
            f"reached. Delete unused {noun} or upgrade your plan to add more."
        )
