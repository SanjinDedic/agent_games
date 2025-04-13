from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
import logging
import asyncio
from typing import Optional

from backend.database.db_models import Institution
from backend.models_api import ErrorResponseModel, ResponseModel
from backend.routes.auth.auth_core import get_current_user, verify_admin_or_institution
from backend.routes.auth.auth_db import get_db
from backend.routes.diagnostics.diagnostics_models import (
    DiagnosticsResponse,
    LogsRequest,
    ResourceUsage,
    ServiceName,
    ServiceStatus,
    SystemResources,
)
from backend.routes.diagnostics.diagnostics_utils import (
    get_all_service_logs,
    get_service_logs,
    get_system_resources,
    get_all_services_status,
    get_service_status,
    get_service_resource_usage,
    get_all_services_resource_usage,
)

logger = logging.getLogger(__name__)

diagnostics_router = APIRouter()

# Helper function to check Docker access
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
    service: ServiceName = ServiceName.ALL,
    tail: Optional[int] = 100,
    since: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get logs for one or all services"""
    has_access = await check_docker_access(current_user, session)
    if not has_access:
        return ErrorResponseModel(
            status="error",
            message="You don't have Docker access. Please contact the administrator.",
        )

    try:
        if service == ServiceName.ALL:
            logs = get_all_service_logs(tail, since)
            return ResponseModel(
                status="success",
                message="Logs retrieved successfully",
                data={"logs": logs},
            )
        else:
            logs = get_service_logs(service.value, tail, since)
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


# NEW ENDPOINT: Fast overview without resource stats
@diagnostics_router.get("/basic-overview", response_model=ResponseModel)
@verify_admin_or_institution
async def get_basic_overview(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get basic system overview without resource-intensive stats"""
    has_access = await check_docker_access(current_user, session)
    if not has_access:
        return ErrorResponseModel(
            status="error",
            message="You don't have Docker access. Please contact the administrator.",
        )

    try:
        # Get quick status information without resource stats
        system_resources = get_system_resources()
        statuses = get_all_services_status()

        return ResponseModel(
            status="success",
            message="Basic system overview retrieved successfully",
            data={
                "system": system_resources,
                "statuses": statuses,
            },
        )
    except Exception as e:
        logger.error(f"Error retrieving basic overview: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve basic overview: {str(e)}"
        )


# NEW ENDPOINT: Get resource stats only
@diagnostics_router.get("/resource-stats", response_model=ResponseModel)
@verify_admin_or_institution
async def get_resource_stats(
    service: ServiceName = ServiceName.ALL,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get resource usage stats (the slow part) for one or all services"""
    has_access = await check_docker_access(current_user, session)
    if not has_access:
        return ErrorResponseModel(
            status="error",
            message="You don't have Docker access. Please contact the administrator.",
        )

    try:
        if service != ServiceName.ALL:
            # Get resource usage for a single service
            usage = get_service_resource_usage(service.value)
            return ResponseModel(
                status="success",
                message=f"Resource usage for {service.value} retrieved successfully",
                data={"resources": {service.value: usage}},
            )
        else:
            # Get resource usage for all services
            service_usage = get_all_services_resource_usage()

            return ResponseModel(
                status="success",
                message="Resource usage retrieved successfully",
                data={"resources": service_usage},
            )
    except Exception as e:
        logger.error(f"Error retrieving resource stats: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve resource stats: {str(e)}"
        )


# Keep the original overview endpoint for backward compatibility
@diagnostics_router.get("/overview", response_model=ResponseModel)
@verify_admin_or_institution
async def get_overview(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get comprehensive overview of all services and system status"""
    has_access = await check_docker_access(current_user, session)
    if not has_access:
        return ErrorResponseModel(
            status="error",
            message="You don't have Docker access. Please contact the administrator.",
        )

    try:
        # Get resource usage for all services
        service_usage = get_all_services_resource_usage()

        # Get status for all services
        statuses = get_all_services_status()

        # Get system resources
        system_resources = get_system_resources()

        # Combine all data
        return ResponseModel(
            status="success",
            message="System overview retrieved successfully",
            data={
                "resources": service_usage,
                "statuses": statuses,
                "system": system_resources,
            },
        )
    except Exception as e:
        logger.error(f"Error retrieving system overview: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve system overview: {str(e)}"
        )


@diagnostics_router.get("/status", response_model=ResponseModel)
@verify_admin_or_institution
async def get_status(
    service: Optional[ServiceName] = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get status for one or all services"""
    # Check Docker access
    has_access = await check_docker_access(current_user, session)
    if not has_access:
        return ErrorResponseModel(
            status="error",
            message="You don't have Docker access. Please contact the administrator.",
        )

    try:
        if service and service != ServiceName.ALL:
            # Get status for a single service
            status = get_service_status(service.value)
            return ResponseModel(
                status="success",
                message=f"Status for {service.value} retrieved successfully",
                data={"status": {service.value: status}},
            )
        else:
            # Get status for all services
            statuses = get_all_services_status()

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
