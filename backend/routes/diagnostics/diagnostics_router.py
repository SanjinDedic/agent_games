from fastapi import APIRouter, Depends

from backend.routes.auth.auth_core import get_current_user, verify_admin_or_institution
from backend.routes.diagnostics.diagnostics_utils import get_all_services_status
from backend.routes.tutorial.pyodide_support import get_pyodide_fallback_stats

diagnostics_router = APIRouter()

# An error while collecting service status surfaces as a 500 rather than a
# masked 200. Each route returns its payload directly.


@diagnostics_router.get("/status")
@verify_admin_or_institution
async def get_status(
    current_user: dict = Depends(get_current_user),
):
    """Get health status for backing services (currently just Valkey)."""
    return {"statuses": await get_all_services_status()}


@diagnostics_router.get("/pyodide-fallbacks")
@verify_admin_or_institution
async def get_pyodide_fallbacks(
    current_user: dict = Depends(get_current_user),
):
    """Per-day counts of browser runs that fell back to the server.

    The migration-readiness dial for in-browser (Pyodide) execution:
    a sustained zero here means the exercise fallback path can be deleted.
    Counters live in Valkey with a 30-day TTL (pyodide_support.py); each
    occurrence is also logged by the API as a warning.
    """
    return get_pyodide_fallback_stats()
