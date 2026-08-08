from fastapi import APIRouter, Depends

from backend.routes.auth.auth_core import require_admin
from backend.routes.diagnostics.diagnostics_utils import get_all_services_status

diagnostics_router = APIRouter()

# Business failures surface via the HTTP status line: an error while collecting
# service status surfaces as a 500 rather than a masked 200. The route returns
# its payload directly.


@diagnostics_router.get("/status")
async def get_status(
    current_user: dict = Depends(require_admin),
):
    """Get health status for the Celery broker and worker services"""
    return {"statuses": await get_all_services_status()}
