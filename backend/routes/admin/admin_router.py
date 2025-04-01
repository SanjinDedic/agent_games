import logging

import httpx
from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.admin.admin_db import (
    create_agent_team,
    create_api_key,
    create_institution,
    delete_all_demo_teams_and_subs,
    delete_institution,
    get_all_demo_users,
    get_all_institutions,
    toggle_institution_docker_access,
    update_institution,
)
from backend.routes.admin.admin_models import (
    CreateAgentAPIKey,
    CreateAgentTeam,
    CreateInstitution,
    DeleteInstitution,
    InstitutionUpdate,
    ToggleDockerAccess,
)
from backend.routes.auth.auth_core import get_current_user, verify_admin_role
from backend.routes.auth.auth_db import get_db

logger = logging.getLogger(__name__)

admin_router = APIRouter()


# Institution management endpoints
@admin_router.post("/institution-create", response_model=ResponseModel)
@verify_admin_role
async def create_institution_endpoint(
    institution: CreateInstitution,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new institution"""
    try:
        data = create_institution(session, institution)
        return ResponseModel(
            status="success", message="Institution created successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error creating institution: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to create institution: {str(e)}"
        )


@admin_router.post("/institution-update", response_model=ResponseModel)
@verify_admin_role
async def update_institution_endpoint(
    institution: InstitutionUpdate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update an institution"""
    try:
        data = update_institution(session, institution)
        return ResponseModel(
            status="success", message="Institution updated successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error updating institution: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to update institution: {str(e)}"
        )


@admin_router.post("/institution-delete", response_model=ResponseModel)
@verify_admin_role
async def delete_institution_endpoint(
    institution: DeleteInstitution,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Delete an institution and all associated teams and leagues"""
    try:
        msg = delete_institution(session, institution.id)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error deleting institution: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to delete institution: {str(e)}"
        )


@admin_router.get("/get-all-institutions", response_model=ResponseModel)
@verify_admin_role
async def get_institutions_endpoint(
    session: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all institutions"""
    try:
        institutions = get_all_institutions(session)
        return ResponseModel(
            status="success",
            message="Institutions retrieved successfully",
            data=institutions,
        )
    except Exception as e:
        logger.error(f"Error retrieving institutions: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve institutions: {str(e)}"
        )


@admin_router.post("/toggle-docker-access", response_model=ResponseModel)
@verify_admin_role
async def toggle_docker_access_endpoint(
    access: ToggleDockerAccess,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Toggle Docker access for an institution"""
    try:
        msg = toggle_institution_docker_access(
            session, access.institution_id, access.enable
        )
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        logger.error(f"Error toggling Docker access: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to toggle Docker access: {str(e)}"
        )


# Agent-related endpoints
@admin_router.post("/create-agent-team", response_model=ResponseModel)
@verify_admin_role
async def create_agent_team_endpoint(
    request: CreateAgentTeam,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new agent team"""
    try:
        data = create_agent_team(session, request)
        return ResponseModel(
            status="success", message="Agent team created successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error creating agent team: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to create agent team: {str(e)}"
        )


@admin_router.post("/create-agent-api-key", response_model=ResponseModel)
@verify_admin_role
async def create_agent_api_key_endpoint(
    request: CreateAgentAPIKey,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Create a new API key for an agent team"""
    try:
        data = create_api_key(session, request.team_id)
        return ResponseModel(
            status="success", message="API key created successfully", data=data
        )
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to create API key: {str(e)}"
        )


# System monitoring endpoints
@admin_router.get("/get-validator-logs", response_model=ResponseModel)
@verify_admin_role
async def get_validator_logs_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """Get logs from validator service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/logs")
            if response.status_code == 200:
                return ResponseModel(
                    status="success",
                    message="Validator logs retrieved successfully",
                    data={"logs": response.json()["logs"]},
                )
            else:
                return ErrorResponseModel(
                    status="error",
                    message=f"Failed to retrieve validator logs: {response.text}",
                )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"Failed to connect to validator service: {str(e)}"
        )

@admin_router.get("/get-simulator-logs", response_model=ResponseModel)
@verify_admin_role
async def get_simulator_logs_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """Get logs from simulator service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/logs")
            if response.status_code == 200:
                return ResponseModel(
                    status="success",
                    message="Simulator logs retrieved successfully",
                    data={"logs": response.json()["logs"]},
                )
            else:
                return ErrorResponseModel(
                    status="error",
                    message=f"Failed to retrieve simulator logs: {response.text}",
                )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"Failed to connect to simulator service: {str(e)}"
        )

# Demo user management endpoints
@admin_router.get("/get_all_demo_users", response_model=ResponseModel)
@verify_admin_role
async def get_all_demo_users_endpoint(
    session: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Get the name, number of submissions and time created for all demo users"""
    try:
        demo_users = get_all_demo_users(session)
        return ResponseModel(
            status="success", message="Demo users fetched successfully", data=demo_users
        )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"Failed to get the demo users{str(e)}"
        )

@admin_router.post("/delete_demo_teams_and_subs", response_model=ResponseModel)
@verify_admin_role
async def delete_all_demo_teams_and_submissions(
    session: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Deletes all demo teams and submissions"""
    try:
        delete_all_demo_teams_and_subs(session)
        return ResponseModel(
            status="success", message="All demo users deleted", data=None
        )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"Failed to delete demo users: {str(e)}"
        )
