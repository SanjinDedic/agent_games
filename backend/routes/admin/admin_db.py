import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union

import pytz
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, select

from backend.database.db_models import (
    AgentAPIKey,
    DemoUser,
    Institution,
    League,
    LeagueType,
    SimulationResult,
    SimulationResultItem,
    Submission,
    Team,
    TeamType,
    get_password_hash,
)
from backend.routes.admin.admin_models import (
    CreateAgentTeam,
    CreateInstitution,
    InstitutionUpdate,
)

logger = logging.getLogger(__name__)
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


class InstitutionError(Exception):
    """Base exception for all institution-related errors"""

    pass


def create_institution(session: Session, institution_data: CreateInstitution) -> Dict:
    """Create a new institution"""
    existing_institution = session.exec(
        select(Institution).where(Institution.name == institution_data.name)
    ).first()

    if existing_institution:
        raise InstitutionError(
            f"Institution with name '{institution_data.name}' already exists"
        )

    try:
        institution = Institution(
            name=institution_data.name,
            contact_person=institution_data.contact_person,
            contact_email=institution_data.contact_email,
            created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
            subscription_active=True,
            subscription_expiry=institution_data.subscription_expiry,
            docker_access=institution_data.docker_access,
        )
        institution.set_password(institution_data.password)

        session.add(institution)
        session.commit()
        session.refresh(institution)

        return {
            "id": institution.id,
            "name": institution.name,
            "contact_person": institution.contact_person,
        }
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating institution: {e}")
        raise InstitutionError(f"Failed to create institution: {str(e)}")


def update_institution(session: Session, institution_data: InstitutionUpdate) -> Dict:
    """Update an existing institution"""
    institution = session.get(Institution, institution_data.id)

    if not institution:
        raise InstitutionError(f"Institution with ID {institution_data.id} not found")

    try:
        # Update fields if provided
        if institution_data.name is not None:
            institution.name = institution_data.name
        if institution_data.contact_person is not None:
            institution.contact_person = institution_data.contact_person
        if institution_data.contact_email is not None:
            institution.contact_email = institution_data.contact_email
        if institution_data.subscription_active is not None:
            institution.subscription_active = institution_data.subscription_active
        if institution_data.subscription_expiry is not None:
            institution.subscription_expiry = institution_data.subscription_expiry
        if institution_data.docker_access is not None:
            institution.docker_access = institution_data.docker_access
        if institution_data.password is not None:
            institution.set_password(institution_data.password)

        session.add(institution)
        session.commit()
        session.refresh(institution)

        return {
            "id": institution.id,
            "name": institution.name,
            "contact_person": institution.contact_person,
        }
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating institution: {e}")
        raise InstitutionError(f"Failed to update institution: {str(e)}")


def delete_institution(session: Session, institution_id: int) -> str:
    """Delete an institution and all associated teams and leagues"""
    institution = session.get(Institution, institution_id)

    if not institution:
        raise InstitutionError(f"Institution with ID {institution_id} not found")

    try:
        # Get all teams for this institution
        teams = session.exec(
            select(Team).where(Team.institution_id == institution_id)
        ).all()

        team_ids = [team.id for team in teams]

        # Delete submissions for these teams
        session.exec(delete(Submission).where(Submission.team_id.in_(team_ids)))

        # Delete simulation result items for these teams
        session.exec(
            delete(SimulationResultItem).where(
                SimulationResultItem.team_id.in_(team_ids)
            )
        )

        # Delete teams
        session.exec(delete(Team).where(Team.institution_id == institution_id))

        # Get leagues for this institution
        leagues = session.exec(
            select(League).where(League.institution_id == institution_id)
        ).all()

        league_ids = [league.id for league in leagues]

        # Delete simulation results for these leagues
        session.exec(
            delete(SimulationResult).where(SimulationResult.league_id.in_(league_ids))
        )

        # Delete leagues
        session.exec(delete(League).where(League.institution_id == institution_id))

        # Finally delete the institution
        session.delete(institution)
        session.commit()

        return f"Institution '{institution.name}' and all associated data deleted successfully"
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting institution: {e}")
        raise InstitutionError(f"Failed to delete institution: {str(e)}")


def get_all_institutions(session: Session) -> Dict:
    """Get all institutions"""
    try:
        institutions = session.exec(select(Institution)).all()
        return {
            "institutions": [
                {
                    "id": inst.id,
                    "name": inst.name,
                    "contact_person": inst.contact_person,
                    "contact_email": inst.contact_email,
                    "created_date": inst.created_date,
                    "subscription_active": inst.subscription_active,
                    "subscription_expiry": inst.subscription_expiry,
                    "docker_access": inst.docker_access,
                    "team_count": len(inst.teams),
                    "league_count": len(inst.leagues),
                }
                for inst in institutions
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving institutions: {e}")
        raise InstitutionError(f"Failed to retrieve institutions: {str(e)}")


def toggle_institution_docker_access(
    session: Session, institution_id: int, enable: bool
) -> str:
    """Toggle Docker access for an institution"""
    institution = session.get(Institution, institution_id)

    if not institution:
        raise InstitutionError(f"Institution with ID {institution_id} not found")

    try:
        institution.docker_access = enable
        session.add(institution)
        session.commit()

        status = "enabled" if enable else "disabled"
        return f"Docker access {status} for institution '{institution.name}'"
    except Exception as e:
        session.rollback()
        logger.error(f"Error toggling Docker access: {e}")
        raise InstitutionError(f"Failed to toggle Docker access: {str(e)}")


# Demo user management functions
def get_all_demo_users(session: Session):
    """
    Retrieve all demo users along with their team, league, and submission details.
    """
    try:
        demo_teams = session.exec(select(Team).where(Team.is_demo == True)).all()
        result = []
        if len(demo_teams) == 0:
            return {"demo_users": []}

        for team in demo_teams:
            latest_submission = session.exec(
                select(Submission)
                .where(Submission.team_id == team.id)
                .order_by(Submission.timestamp.desc())
            ).first()
            # Add a null check before accessing .timestamp
            latest_submission_timestamp = None
            if latest_submission is not None:
                latest_submission_timestamp = latest_submission.timestamp
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
                    "number_of_submissions": len(team.submissions),
                    "latest_submission": latest_submission_timestamp,
                }
            )
        return {"demo_users": result}

    except Exception as e:
        session.rollback()
        raise


def delete_all_demo_teams_and_subs(session):
    """Delete all demo teams and submissions"""
    all_demo_teams = session.exec(select(Team).where(Team.is_demo == True)).all()

    team_ids = [team.id for team in all_demo_teams]

    # First, delete all submissions from these teams
    session.exec(delete(Submission).where(Submission.team_id.in_(team_ids)))
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
    try:
        # Check if league exists and is agent type
        league = session.get(League, team_data.league_id)
        if not league:
            raise ValueError(f"League with ID {team_data.league_id} not found")
        if league.league_type != LeagueType.AGENT:
            raise ValueError("Can only create agent teams in agent leagues")

        # Create team
        team = Team(
            name=team_data.name,
            school_name="AI Agent",
            team_type=TeamType.AGENT,
            league_id=team_data.league_id,
            institution_id=league.institution_id,  # Set the institution_id from the league
        )
        session.add(team)
        session.commit()
        session.refresh(team)

        return {"team_id": team.id, "name": team.name, "league": league.name}

    except Exception as e:
        session.rollback()
        raise


def create_api_key(session: Session, team_id: int) -> Dict:
    """Create a new API key for an agent team"""
    try:
        team = session.get(Team, team_id)
        if not team:
            raise ValueError(f"Team with ID {team_id} not found")
        if team.team_type != TeamType.AGENT:
            raise ValueError("Can only create API keys for agent teams")

        # Generate secure API key
        api_key = secrets.token_urlsafe(32)

        # Create API key record
        key_record = AgentAPIKey(key=api_key, team_id=team_id)
        session.add(key_record)
        session.commit()

        return {"team_id": team_id, "api_key": api_key}

    except Exception as e:
        session.rollback()
        raise
