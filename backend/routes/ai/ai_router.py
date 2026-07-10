import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.database.db_session import get_db
from backend.routes.ai.ai_db import (
    get_api_keys,
    get_stored_key,
    get_team_in_league,
    update_api_key,
)
from backend.routes.ai.ai_models import (
    PlagiarismRequest,
    UpdateAPIKeysRequest,
    ValidateAPIKeyRequest,
)
from backend.routes.ai.clients import CLIENT_REGISTRY, get_client_class
from backend.routes.ai.plagiarism_service import assess_team_for_plagiarism
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_or_institution,
    verify_admin_role,
)
from backend.routes.institution.institution_db import get_league_by_id
from backend.routes.institution.institution_router import _resolve_institution

logger = logging.getLogger(__name__)

ai_router = APIRouter()

# Business failures raise domain exceptions, mapped centrally by the handlers in
# api.py: LeagueNotFoundError -> 404, InstitutionAccessError -> 403,
# UnknownProviderError / NoApiKeyError / NoSubmissionsError -> 400,
# PayloadTooLargeError -> 413, LLMResponseError -> 502, AIRequestTimeoutError -> 504.
# Missing resources and bad tokens raise HTTPException directly. Anything unexpected
# surfaces as a 500 rather than a masked 200. Each route returns its payload directly;
# the HTTP status line is the status.


@ai_router.get("/api-keys")
@verify_admin_role
async def get_api_keys_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get the current AI provider API keys (masked for security)."""
    return get_api_keys(session, CLIENT_REGISTRY.keys())


@ai_router.post("/api-keys")
@verify_admin_role
async def update_api_keys_endpoint(
    keys_data: UpdateAPIKeysRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update AI provider API keys."""
    for provider in CLIENT_REGISTRY:
        new_key = getattr(keys_data, f"{provider}_api_key", None)
        if new_key is not None:
            update_api_key(session, provider, new_key)

    return get_api_keys(session, CLIENT_REGISTRY.keys())


@ai_router.post("/api-keys/validate")
@verify_admin_role
async def validate_api_key_endpoint(
    request_data: ValidateAPIKeyRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Validate an AI provider API key by making a test call."""
    provider = request_data.provider
    api_key = request_data.api_key

    client_class = get_client_class(provider)  # UnknownProviderError -> 400

    # No key in the request: fall back to the stored key, if any.
    if not api_key:
        api_key = get_stored_key(session, provider)
        if not api_key:
            return {
                "valid": False,
                "message": "No API key configured for this provider",
            }

    valid = await client_class(api_key).check_key()  # AIRequestTimeoutError -> 504
    return {"valid": valid}


@ai_router.post("/assess-plagiarism")
@verify_admin_or_institution
async def assess_plagiarism_endpoint(
    request: PlagiarismRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Run plagiarism + AI-generation assessment against a team's submission history."""
    institution_id, is_admin = _resolve_institution(current_user)
    if not institution_id:
        raise HTTPException(status_code=400, detail="Institution ID not found in token")

    # Verify caller owns this league (admin bypasses ownership check).
    # LeagueNotFoundError -> 404, InstitutionAccessError -> 403.
    league = get_league_by_id(
        session, request.league_id, institution_id, is_admin=is_admin
    )

    # Verify the team exists and belongs to that league.
    team = get_team_in_league(session, request.team_id, request.league_id)
    if not team:
        raise HTTPException(
            status_code=404,
            detail=f"Team {request.team_id} not found in league {request.league_id}",
        )

    # Audit log.
    logger.info(
        "Plagiarism assessment: caller_role=%s caller_institution_id=%s team=%s league_id=%s",
        current_user.get("role"),
        current_user.get("institution_id"),
        team.name,
        request.league_id,
    )

    # NoApiKeyError -> 400, NoSubmissionsError -> 400, PayloadTooLargeError -> 413,
    # LLMResponseError -> 502.
    report = await assess_team_for_plagiarism(
        session, team, request.league_id, game_name=league.game
    )
    return report.model_dump()
