from fastapi import APIRouter, Depends
from sqlmodel import Session
import logging

from backend.database.db_models import Institution
from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.auth.auth_core import get_current_user, verify_admin_or_institution
from backend.routes.auth.auth_db import get_db
from backend.routes.diagnostics.diagnostics_models import ServiceName
from backend.routes.diagnostics.diagnostics_utils import (
    get_service_logs,
    get_all_services_status,
)

logger = logging.getLogger(__name__)

diagnostics_router = APIRouter()


async def check_docker_access(current_user: dict, session: Session) -> bool:
    """Check if the current user has Docker access"""
    if current_user["role"] == "admin":
        return True

    if current_user["role"] == "institution":
        institution_id = current_user.get("institution_id")
        if not institution_id:
            return False

        institution = session.get(Institution, institution_id)
        if not institution or not institution.docker_access:
            return False

        return True

    return False


@diagnostics_router.get("/logs", response_model=ResponseModel)
@verify_admin_or_institution
async def get_logs(
    service: ServiceName,
    tail: int = 100,
    since: str = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    print("VOLUME BIND WORKINGX")
    """Get logs for validator or simulator service"""
    has_access = await check_docker_access(current_user, session)
    if not has_access:
        return ErrorResponseModel(
            status="error",
            message="You don't have Docker access. Please contact the administrator.",
        )

    try:
        logs = get_service_logs(service_name=service.value, tail=tail)
        return ResponseModel(
            status="success",
            message=f"Logs for {service.value} retrieved successfully",
            data={"logs": {service.value: logs}},
        )
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve logs: {str(e)}"
        )


@diagnostics_router.get("/status", response_model=ResponseModel)
@verify_admin_or_institution
async def get_status(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get health status for validator and simulator services"""
    has_access = await check_docker_access(current_user, session)
    if not has_access:
        return ErrorResponseModel(
            status="error",
            message="You don't have Docker access. Please contact the administrator.",
        )

    try:
        statuses = await get_all_services_status()
        return ResponseModel(
            status="success",
            message="Services status retrieved successfully",
            data={"statuses": statuses},
        )
    except Exception as e:
        logger.error(f"Error retrieving service status: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve service status: {str(e)}"
        )
