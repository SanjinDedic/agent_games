from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.routes.admin.admin_db import (
    clear_institution_data,
    create_agent_team,
    create_api_key,
    create_institution,
    delete_all_demo_teams_and_subs,
    delete_institution,
    export_institution_data,
    get_all_demo_users,
    get_all_institutions,
    update_institution,
)
from backend.routes.admin.admin_models import (
    ClearInstitutionData,
    CreateAgentAPIKey,
    CreateAgentTeam,
    CreateInstitution,
    DeleteInstitution,
    InstitutionUpdate,
)
from backend.routes.auth.auth_core import get_current_user, verify_admin_role
from backend.database.db_session import get_db

admin_router = APIRouter()

# Business failures raise domain exceptions (InstitutionNotFoundError -> 404,
# InstitutionExistsError -> 409, AgentTeamError -> 400), mapped centrally by the
# handlers in api.py. Anything unexpected surfaces as a 500 rather than a masked
# 200. Each route returns its payload directly; the HTTP status line is the status.


# Institution management endpoints
@admin_router.post("/institution-create")
@verify_admin_role
async def create_institution_endpoint(
    institution: CreateInstitution,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new institution."""
    return create_institution(session, institution)


@admin_router.post("/institution-update")
@verify_admin_role
async def update_institution_endpoint(
    institution: InstitutionUpdate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update an institution."""
    return update_institution(session, institution)


@admin_router.post("/institution-delete")
@verify_admin_role
async def delete_institution_endpoint(
    institution: DeleteInstitution,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete an institution and all associated teams and leagues."""
    return {"message": delete_institution(session, institution.id)}


@admin_router.post("/institution-clear-data")
@verify_admin_role
async def clear_institution_data_endpoint(
    request: ClearInstitutionData,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Clear all teams/leagues/submissions/results for an institution while keeping
    the institution row and its auto-created 'unassigned' league."""
    counts = clear_institution_data(session, request.id)
    message = (
        f"Cleared institution data: {counts['teams_deleted']} team(s), "
        f"{counts['leagues_deleted']} league(s) removed"
    )
    return {"message": message, **counts}


@admin_router.get("/institution-export/{institution_id}")
@verify_admin_role
async def export_institution_endpoint(
    institution_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Return a JSON dump of every record belonging to one institution."""
    return export_institution_data(session, institution_id)


@admin_router.get("/get-all-institutions")
@verify_admin_role
async def get_institutions_endpoint(
    session: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all institutions."""
    return get_all_institutions(session)


# Agent-related endpoints
@admin_router.post("/create-agent-team")
@verify_admin_role
async def create_agent_team_endpoint(
    request: CreateAgentTeam,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new agent team."""
    return create_agent_team(session, request)


@admin_router.post("/create-agent-api-key")
@verify_admin_role
async def create_agent_api_key_endpoint(
    request: CreateAgentAPIKey,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new API key for an agent team."""
    return create_api_key(session, request.team_id)


# Demo user management endpoints
@admin_router.get("/get_all_demo_users")
@verify_admin_role
async def get_all_demo_users_endpoint(
    session: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Get the name, number of submissions and time created for all demo users."""
    return get_all_demo_users(session)


@admin_router.post("/delete_demo_teams_and_subs")
@verify_admin_role
async def delete_all_demo_teams_and_submissions(
    session: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Delete all demo teams and submissions."""
    delete_all_demo_teams_and_subs(session)
    return {"message": "All demo users deleted"}
