import json
import logging
import secrets
from datetime import timedelta
from typing import Dict, List, Tuple, Union

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from backend.database.db_models import (
    AgentAPIKey,
    DemoUser,
    Institution,
    InstitutionSubscription,
    League,
    LeagueType,
    LeagueTutorial,
    SimulationResult,
    SimulationResultItem,
    Submission,
    SubmissionMetadata,
    SupportTicket,
    SupportTicketAttachment,
    Team,
    TeamType,
    get_password_hash,
)
from backend.database.submission_helpers import delete_submissions_for_teams
from backend.routes.admin.admin_models import (
    CreateAgentTeam,
    CreateInstitution,
    InstitutionUpdate,
)
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)


class InstitutionError(Exception):
    """Base exception for all institution-related errors"""

    pass


class InstitutionNotFoundError(InstitutionError):
    """Raised when the target institution does not exist (maps to HTTP 404)."""

    pass


class InstitutionExistsError(InstitutionError):
    """Raised when an institution name collides with an existing one (maps to HTTP 409)."""

    pass


class AgentTeamError(ValueError):
    """Raised for invalid agent-team / API-key operations (maps to HTTP 400).

    Subclasses ValueError so existing callers/tests that catch ValueError keep working.
    """

    pass


def create_institution(session: Session, institution_data: CreateInstitution) -> Dict:
    """Create a new institution"""
    existing_institution = session.exec(
        select(Institution).where(Institution.name == institution_data.name)
    ).first()

    if existing_institution:
        raise InstitutionExistsError(
            f"Institution with name '{institution_data.name}' already exists"
        )

    now = utc_now()
    institution = Institution(
        name=institution_data.name,
        contact_person=institution_data.contact_person,
        contact_email=institution_data.contact_email,
        created_date=now,
    )
    institution.set_password(institution_data.password)

    session.add(institution)
    session.flush()  # Get the ID for the new institution

    # Admin-granted access: subscription state lives on the 1:1 record.
    session.add(
        InstitutionSubscription(
            institution_id=institution.id,
            payment_method="admin",
            subscription_active=True,
            subscription_expiry=institution_data.subscription_expiry,
            created_date=now,
        )
    )

    # Create unassigned league for this institution
    unassigned_league = League(
        name="unassigned",
        created_date=utc_now(),
        expiry_date=(
            utc_now()
            + timedelta(days=365)  # Long expiry for unassigned league
        ),
        game="greedy_pig",  # Default game
        league_type=LeagueType.INSTITUTION,
        institution_id=institution.id,
    )
    session.add(unassigned_league)

    session.commit()
    session.refresh(institution)

    return {
        "id": institution.id,
        "name": institution.name,
        "contact_person": institution.contact_person,
    }


def update_institution(session: Session, institution_data: InstitutionUpdate) -> Dict:
    """Update an existing institution"""
    institution = session.get(Institution, institution_data.id)

    if not institution:
        raise InstitutionNotFoundError(
            f"Institution with ID {institution_data.id} not found"
        )

    try:
        # Update fields if provided
        if institution_data.name is not None:
            institution.name = institution_data.name
        if institution_data.contact_person is not None:
            institution.contact_person = institution_data.contact_person
        if institution_data.contact_email is not None:
            institution.contact_email = institution_data.contact_email
        if institution_data.password is not None:
            institution.set_password(institution_data.password)

        # Subscription fields live on the 1:1 InstitutionSubscription record.
        if (
            institution_data.subscription_active is not None
            or institution_data.subscription_expiry is not None
        ):
            subscription = institution.subscription
            if subscription is None:
                subscription = InstitutionSubscription(
                    institution_id=institution.id,
                    payment_method="admin",
                    subscription_active=True,
                    subscription_expiry=(
                        institution_data.subscription_expiry
                        or utc_now()
                    ),
                    created_date=utc_now(),
                )
            if institution_data.subscription_active is not None:
                subscription.subscription_active = institution_data.subscription_active
            if institution_data.subscription_expiry is not None:
                subscription.subscription_expiry = institution_data.subscription_expiry
            session.add(subscription)

        session.add(institution)
        session.commit()
        session.refresh(institution)

        return {
            "id": institution.id,
            "name": institution.name,
            "contact_person": institution.contact_person,
        }
    except IntegrityError as e:
        session.rollback()
        raise InstitutionExistsError(
            f"Institution name '{institution_data.name}' already exists"
        )


def _purge_institution_data(
    session: Session, institution_id: int, *, keep_unassigned: bool
) -> Dict:
    """Delete every child row owned by an institution (teams, leagues, submissions,
    simulation results, agent API keys, support tickets + attachments).

    When keep_unassigned is True, the auto-created 'unassigned' league row is preserved
    (its child teams are still wiped). Does not delete the Institution row itself and
    does not commit; the caller is responsible for that.

    Returns counts for the UI toast.
    """
    teams = session.exec(
        select(Team).where(Team.institution_id == institution_id)
    ).all()
    team_ids = [t.id for t in teams]

    leagues = session.exec(
        select(League).where(League.institution_id == institution_id)
    ).all()
    league_ids = [lg.id for lg in leagues]
    leagues_to_keep = (
        {lg.id for lg in leagues if lg.name == "unassigned"} if keep_unassigned else set()
    )

    # Tickets attached to the institution directly, plus any from its teams.
    ticket_id_set: set[int] = set(
        session.exec(
            select(SupportTicket.id).where(
                SupportTicket.institution_id == institution_id
            )
        ).all()
    )
    if team_ids:
        ticket_id_set.update(
            session.exec(
                select(SupportTicket.id).where(SupportTicket.team_id.in_(team_ids))
            ).all()
        )
    ticket_ids = list(ticket_id_set)

    # Capture S3 keys before deleting attachment rows so we can clean up after commit.
    s3_keys: List[str] = []
    if ticket_ids:
        s3_keys = list(
            session.exec(
                select(SupportTicketAttachment.s3_key).where(
                    SupportTicketAttachment.ticket_id.in_(ticket_ids)
                )
            ).all()
        )
        session.exec(
            delete(SupportTicketAttachment).where(
                SupportTicketAttachment.ticket_id.in_(ticket_ids)
            )
        )
        session.exec(delete(SupportTicket).where(SupportTicket.id.in_(ticket_ids)))

    if team_ids:
        delete_submissions_for_teams(session, team_ids)
        session.exec(
            delete(SimulationResultItem).where(
                SimulationResultItem.team_id.in_(team_ids)
            )
        )
        session.exec(delete(AgentAPIKey).where(AgentAPIKey.team_id.in_(team_ids)))
        session.exec(delete(Team).where(Team.institution_id == institution_id))

    if league_ids:
        session.exec(
            delete(SimulationResult).where(SimulationResult.league_id.in_(league_ids))
        )

    leagues_to_delete = [lid for lid in league_ids if lid not in leagues_to_keep]
    if leagues_to_delete:
        session.exec(
            delete(LeagueTutorial).where(
                LeagueTutorial.league_id.in_(leagues_to_delete)
            )
        )
        session.exec(delete(League).where(League.id.in_(leagues_to_delete)))

    return {
        "team_ids": team_ids,
        "league_ids": league_ids,
        "leagues_deleted": len(leagues_to_delete),
        "ticket_ids": ticket_ids,
        "s3_keys": s3_keys,
    }


def _cleanup_s3_attachments(s3_keys: List[str]) -> None:
    """Best-effort delete of S3 attachment objects. Import lazily so that callers
    without S3 configured (unit tests) don't blow up at import time."""
    if not s3_keys:
        return
    try:
        from backend.routes.support.support_s3 import delete_attachment
    except Exception as exc:
        logger.warning(f"Could not import S3 client for attachment cleanup: {exc}")
        return
    for key in s3_keys:
        try:
            delete_attachment(key)
        except Exception as exc:
            logger.warning(f"Failed to delete S3 attachment {key}: {exc}")


def delete_institution(session: Session, institution_id: int) -> str:
    """Delete an institution and all associated teams, leagues, submissions,
    simulation results, agent API keys, and support tickets."""
    institution = session.get(Institution, institution_id)

    if not institution:
        raise InstitutionNotFoundError(
            f"Institution with ID {institution_id} not found"
        )

    purge = _purge_institution_data(session, institution_id, keep_unassigned=False)
    session.delete(institution)
    session.commit()

    _cleanup_s3_attachments(purge["s3_keys"])

    return (
        f"Institution '{institution.name}' and all associated data deleted successfully"
    )


def clear_institution_data(session: Session, institution_id: int) -> Dict:
    """Wipe all teams/leagues/submissions/results/api keys/tickets for an institution
    while keeping the institution row and its auto-created 'unassigned' league."""
    institution = session.get(Institution, institution_id)

    if not institution:
        raise InstitutionNotFoundError(
            f"Institution with ID {institution_id} not found"
        )

    purge = _purge_institution_data(session, institution_id, keep_unassigned=True)
    session.commit()

    _cleanup_s3_attachments(purge["s3_keys"])

    return {
        "institution_id": institution_id,
        "teams_deleted": len(purge["team_ids"]),
        "leagues_deleted": purge["leagues_deleted"],
        "tickets_deleted": len(purge["ticket_ids"]),
    }


def export_institution_data(session: Session, institution_id: int) -> Dict:
    """Return a JSON-serializable dump of every record belonging to one institution."""
    institution = session.get(Institution, institution_id)

    if not institution:
        raise InstitutionNotFoundError(
            f"Institution with ID {institution_id} not found"
        )

    teams = session.exec(
        select(Team).where(Team.institution_id == institution_id)
    ).all()
    team_ids = [t.id for t in teams]

    leagues = session.exec(
        select(League).where(League.institution_id == institution_id)
    ).all()
    league_ids = [lg.id for lg in leagues]

    metadata_rows = (
        session.exec(
            select(SubmissionMetadata).where(SubmissionMetadata.team_id.in_(team_ids))
        ).all()
        if team_ids
        else []
    )
    meta_ids = [m.id for m in metadata_rows]
    submissions = (
        session.exec(
            select(Submission).where(Submission.metadata_id.in_(meta_ids))
        ).all()
        if meta_ids
        else []
    )

    sim_results = (
        session.exec(
            select(SimulationResult).where(SimulationResult.league_id.in_(league_ids))
        ).all()
        if league_ids
        else []
    )

    sim_items = (
        session.exec(
            select(SimulationResultItem).where(
                SimulationResultItem.team_id.in_(team_ids)
            )
        ).all()
        if team_ids
        else []
    )

    api_keys = (
        session.exec(
            select(AgentAPIKey).where(AgentAPIKey.team_id.in_(team_ids))
        ).all()
        if team_ids
        else []
    )

    ticket_id_set: set[int] = set(
        session.exec(
            select(SupportTicket.id).where(
                SupportTicket.institution_id == institution_id
            )
        ).all()
    )
    if team_ids:
        ticket_id_set.update(
            session.exec(
                select(SupportTicket.id).where(SupportTicket.team_id.in_(team_ids))
            ).all()
        )
    ticket_ids = list(ticket_id_set)

    tickets = (
        session.exec(
            select(SupportTicket).where(SupportTicket.id.in_(ticket_ids))
        ).all()
        if ticket_ids
        else []
    )
    attachments = (
        session.exec(
            select(SupportTicketAttachment).where(
                SupportTicketAttachment.ticket_id.in_(ticket_ids)
            )
        ).all()
        if ticket_ids
        else []
    )
    attachments_by_ticket: Dict[int, list] = {}
    for att in attachments:
        attachments_by_ticket.setdefault(att.ticket_id, []).append(
            att.model_dump(mode="json")
        )

    institution_dump = institution.model_dump(mode="json", exclude={"password_hash"})

    teams_dump = [t.model_dump(mode="json", exclude={"password_hash"}) for t in teams]
    leagues_dump = [lg.model_dump(mode="json") for lg in leagues]
    submissions_dump = [s.model_dump(mode="json") for s in submissions]
    submission_metadata_dump = [m.model_dump(mode="json") for m in metadata_rows]
    sim_results_dump = [r.model_dump(mode="json") for r in sim_results]
    sim_items_dump = [i.model_dump(mode="json") for i in sim_items]

    api_keys_dump = []
    for ak in api_keys:
        masked = ak.model_dump(mode="json", exclude={"key"})
        masked["key_masked"] = (
            f"***{ak.key[-4:]}" if ak.key and len(ak.key) >= 4 else "***"
        )
        api_keys_dump.append(masked)

    tickets_dump = []
    for tk in tickets:
        d = tk.model_dump(mode="json")
        d["attachments"] = attachments_by_ticket.get(tk.id, [])
        tickets_dump.append(d)

    return {
        "schema_version": 1,
        "exported_at": utc_now().isoformat(),
        "institution": institution_dump,
        "leagues": leagues_dump,
        "teams": teams_dump,
        "submissions": submissions_dump,
        "submission_metadata": submission_metadata_dump,
        "simulation_results": sim_results_dump,
        "simulation_result_items": sim_items_dump,
        "agent_api_keys": api_keys_dump,
        "support_tickets": tickets_dump,
    }


def get_all_institutions(session: Session) -> Dict:
    """Get all institutions"""
    institutions = session.exec(select(Institution)).all()
    return {
        "institutions": [
            {
                "id": inst.id,
                "name": inst.name,
                "contact_person": inst.contact_person,
                "contact_email": inst.contact_email,
                "created_date": inst.created_date,
                "subscription_active": (
                    inst.subscription.subscription_active
                    if inst.subscription
                    else None
                ),
                "subscription_expiry": (
                    inst.subscription.subscription_expiry
                    if inst.subscription
                    else None
                ),
                "team_count": len(inst.teams),
                "league_count": len(inst.leagues),
            }
            for inst in institutions
        ]
    }


# Demo user management functions
def get_all_demo_users(session: Session):
    """
    Retrieve all demo users along with their team, league, and submission details.
    """
    demo_teams = session.exec(select(Team).where(Team.is_demo == True)).all()
    result = []
    if len(demo_teams) == 0:
        return {"demo_users": []}

    for team in demo_teams:
        latest_attempt = session.exec(
            select(SubmissionMetadata)
            .where(SubmissionMetadata.team_id == team.id)
            .order_by(SubmissionMetadata.timestamp.desc())
        ).first()
        # Add a null check before accessing .timestamp
        latest_submission_timestamp = None
        if latest_attempt is not None:
            latest_submission_timestamp = latest_attempt.timestamp
        # get the email from the DemoUser table
        matching_demo_user = session.exec(
            select(DemoUser).where(DemoUser.username == team.school_name)
        ).first()  # for the special case of demo users, the username they typed in is saved as the school_name
        email = matching_demo_user.email if matching_demo_user is not None else None
        result.append(
            {
                "demo_team_id": team.id,
                "demo_team_name": team.name,
                "email": email,
                "league_name": team.league.name if team.league else None,
                "number_of_submissions": len(team.submission_attempts),
                "latest_submission": latest_submission_timestamp,
            }
        )
    return {"demo_users": result}


def delete_all_demo_teams_and_subs(session):
    """Delete all demo teams and submissions"""
    all_demo_teams = session.exec(select(Team).where(Team.is_demo == True)).all()

    team_ids = [team.id for team in all_demo_teams]

    # First, delete all submissions from these teams
    delete_submissions_for_teams(session, team_ids)
    # Delete any SimulationResultItems for these teams
    session.exec(
        delete(SimulationResultItem).where(SimulationResultItem.team_id.in_(team_ids))
    )
    # Now delete the teams themselves
    session.exec(delete(Team).where(Team.id.in_(team_ids)))

    session.commit()


# Agent team management functions
def create_agent_team(session: Session, team_data: CreateAgentTeam) -> Dict:
    """Create a new agent team"""
    # Check if league exists and is agent type
    league = session.get(League, team_data.league_id)
    if not league:
        raise AgentTeamError(f"League with ID {team_data.league_id} not found")
    if league.league_type != LeagueType.AGENT:
        raise AgentTeamError("Can only create agent teams in agent leagues")

    # Create team
    team = Team(
        name=team_data.name,
        school_name="AI Agent",
        team_type=TeamType.AGENT,
        league_id=team_data.league_id,
        institution_id=league.institution_id,
    )
    session.add(team)
    session.commit()
    session.refresh(team)

    return {"team_id": team.id, "name": team.name, "league": league.name}


def create_api_key(session: Session, team_id: int) -> Dict:
    """Create a new API key for an agent team"""
    team = session.get(Team, team_id)
    if not team:
        raise AgentTeamError(f"Team with ID {team_id} not found")
    if team.team_type != TeamType.AGENT:
        raise AgentTeamError("Can only create API keys for agent teams")

    # Generate secure API key
    api_key = secrets.token_urlsafe(32)

    # Create API key record
    key_record = AgentAPIKey(key=api_key, team_id=team_id)
    session.add(key_record)
    session.commit()

    return {"team_id": team_id, "api_key": api_key}
