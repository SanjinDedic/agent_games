from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.routes.admin.admin_backup import create_backup, list_backups, restore_backup
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
    RestoreBackup,
    UpdateSupportTicket,
)
from backend.routes.auth.auth_core import get_current_user, verify_admin_role
from backend.database.db_session import get_db
from backend.database.db_models import (
    SupportTicketStatus,
    SupportTicketSubmitterType,
)
from backend.routes.support.support_db import (
    delete_ticket,
    list_tickets,
    update_ticket,
)

admin_router = APIRouter()

# Business failures raise domain exceptions (InstitutionNotFoundError -> 404,
# InstitutionExistsError -> 409, AgentTeamError -> 400, SupportError -> 404),
# mapped centrally by the handlers in api.py. Bad enum values raise HTTPException
# directly. Anything unexpected surfaces as a 500 rather than a masked 200. Each
# route returns its payload directly; the HTTP status line is the status.


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
        f"{counts['leagues_deleted']} league(s), "
        f"{counts['tickets_deleted']} ticket(s) removed"
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


# Database backup endpoints
@admin_router.post("/backup-database")
@verify_admin_role
async def backup_database_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """Create a pg_dump backup and upload to DigitalOcean Spaces."""
    result = create_backup()
    return {"message": f"Backup created: {result['filename']}", **result}


@admin_router.get("/list-backups")
@verify_admin_role
async def list_backups_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """List all database backups in DigitalOcean Spaces."""
    return {"backups": list_backups()}


@admin_router.post("/restore-database")
@verify_admin_role
async def restore_database_endpoint(
    request: RestoreBackup,
    current_user: dict = Depends(get_current_user),
):
    """Restore the database from an S3 backup."""
    result = restore_backup(request.s3_key)
    return {"message": f"Database restored from {result['filename']}", **result}


# Support ticket management endpoints
@admin_router.get("/support-tickets")
@verify_admin_role
async def list_support_tickets_endpoint(
    submitter_type: str = "all",
    status: str | None = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """List support tickets, optionally filtered by submitter type and status."""
    submitter_filter = None
    if submitter_type != "all":
        try:
            submitter_filter = SupportTicketSubmitterType(submitter_type)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid submitter_type: {submitter_type}"
            )

    status_filter = None
    if status:
        try:
            status_filter = SupportTicketStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    tickets = list_tickets(
        session,
        submitter_type=submitter_filter,
        status=status_filter,
    )
    return {"tickets": [t.model_dump(mode="json") for t in tickets]}


@admin_router.post("/support-ticket-update")
@verify_admin_role
async def update_support_ticket_endpoint(
    request: UpdateSupportTicket,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update a support ticket's status and/or admin note."""
    status_enum = None
    if request.status is not None:
        try:
            status_enum = SupportTicketStatus(request.status)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid status: {request.status}"
            )

    updated = update_ticket(
        session,
        ticket_id=request.ticket_id,
        status=status_enum,
        admin_note=request.admin_note,
    )
    return {"ticket": updated.model_dump(mode="json")}


@admin_router.delete("/support-ticket/{ticket_id}")
@verify_admin_role
async def delete_support_ticket_endpoint(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete a support ticket and any associated S3 attachments."""
    return delete_ticket(session, ticket_id)
