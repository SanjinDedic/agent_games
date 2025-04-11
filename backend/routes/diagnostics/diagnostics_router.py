import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

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
    get_all_services_resource_usage,
    get_all_services_status,
    get_service_logs,
    get_service_resource_usage,
    get_service_status,
    get_system_resources,
)

logger = logging.getLogger(__name__)

diagnostics_router = APIRouter()


# Helper function to check Docker access
async def check_docker_access(current_user: dict, session: Session) -> bool:
    """
    Check if the current user has Docker access
    
    Returns:
        bool: True if the user has Docker access, False otherwise
    """
    # Always allow admin access
    if current_user["role"] == "admin":
        return True
    
    # For institutions, check docker_access flag
    if current_user["role"] == "institution":
        institution_id = current_user.get("institution_id")
        if not institution_id:
            return False
        
        institution = session.get(Institution, institution_id)
        if not institution or not institution.docker_access:
            return False
        
        return True
    
    # Default to no access
    return False


@diagnostics_router.post("/logs", response_model=ResponseModel)
@verify_admin_or_institution
async def get_logs(
    request: LogsRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Get logs for one or all services
    """
    # Check Docker access
    has_access = await check_docker_access(current_user, session)
    if not has_access:
        return ErrorResponseModel(
            status="error",
            message="You don't have Docker access. Please contact the administrator.",
        )
    
    try:
        service = request.service
        
        if service == ServiceName.ALL:
            logs = get_all_service_logs(request.tail, request.since)
            return ResponseModel(
                status="success",
                message="Logs retrieved successfully",
                data={"logs": logs},
            )
        else:
            logs = get_service_logs(service.value, request.tail, request.since)
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


@diagnostics_router.get("/resources", response_model=ResponseModel)
@verify_admin_or_institution
async def get_resources(
    service: Optional[ServiceName] = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Get resource usage for one or all services
    """
    # Check Docker access
    has_access = await check_docker_access(current_user, session)
    if not has_access:
        return ErrorResponseModel(
            status="error",
            message="You don't have Docker access. Please contact the administrator.",
        )
    
    try:
        if service and service != ServiceName.ALL:
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
            system_resources = get_system_resources()
            
            return ResponseModel(
                status="success",
                message="Resource usage retrieved successfully",
                data={
                    "services": service_usage,
                    "system": system_resources,
                },
            )
    except Exception as e:
        logger.error(f"Error retrieving resource usage: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve resource usage: {str(e)}"
        )


@diagnostics_router.get("/status", response_model=ResponseModel)
@verify_admin_or_institution
async def get_status(
    service: Optional[ServiceName] = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Get status for one or all services
    """
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


@diagnostics_router.get("/overview", response_model=ResponseModel)
@verify_admin_or_institution
async def get_overview(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """
    Get comprehensive overview of all services and system status
    """
    # Check Docker access
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