import logging

import httpx
from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.database.db_session import get_db
from backend.models_api import ErrorResponseModel, ResponseModel
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
from backend.routes.ai.plagiarism_service import (
    LLMResponseError,
    NoApiKeyError,
    NoSubmissionsError,
    PayloadTooLargeError,
    assess_team_for_plagiarism,
)
from backend.routes.auth.auth_core import (
    get_current_user,
    verify_admin_or_institution,
    verify_admin_role,
)
from backend.routes.institution.institution_db import (
    InstitutionAccessError,
    LeagueNotFoundError,
    get_league_by_id,
)
from backend.routes.institution.institution_router import _resolve_institution

logger = logging.getLogger(__name__)

ai_router = APIRouter()


@ai_router.get("/api-keys", response_model=ResponseModel)
@verify_admin_role
async def get_api_keys_endpoint(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Get the current AI provider API keys (masked for security)"""
    try:
        keys = get_api_keys(session)
        return ResponseModel(
            status="success",
            message="API keys retrieved successfully",
            data=keys,
        )
    except Exception as e:
        logger.error(f"Error retrieving API keys: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to retrieve API keys: {str(e)}"
        )


@ai_router.post("/api-keys", response_model=ResponseModel)
@verify_admin_role
async def update_api_keys_endpoint(
    keys_data: UpdateAPIKeysRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Update AI provider API keys"""
    try:
        if keys_data.openai_api_key is not None:
            update_api_key(session, "openai", keys_data.openai_api_key)

        keys = get_api_keys(session)
        return ResponseModel(
            status="success",
            message="API keys updated successfully",
            data=keys,
        )
    except Exception as e:
        logger.error(f"Error updating API keys: {e}")
        return ErrorResponseModel(
            status="error", message=f"Failed to update API keys: {str(e)}"
        )


@ai_router.post("/api-keys/validate", response_model=ResponseModel)
@verify_admin_role
async def validate_api_key_endpoint(
    request_data: ValidateAPIKeyRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Validate an AI provider API key by making a test call"""
    provider = request_data.provider
    api_key = request_data.api_key

    # If no key provided in the request, validate the stored key
    if not api_key:
        api_key = get_stored_key(session, provider)
        if not api_key:
            return ResponseModel(
                status="success",
                message="No API key configured for this provider",
                data={"valid": False},
            )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider == "openai":
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            else:
                return ErrorResponseModel(
                    status="error",
                    message=f"Unknown provider: {provider}",
                )

            if resp.status_code == 200:
                return ResponseModel(
                    status="success",
                    message="API key is valid",
                    data={"valid": True},
                )
            elif resp.status_code in (401, 403):
                return ResponseModel(
                    status="success",
                    message="API key is invalid or unauthorized",
                    data={"valid": False},
                )
            else:
                return ResponseModel(
                    status="success",
                    message=f"Unexpected response (HTTP {resp.status_code})",
                    data={"valid": False},
                )
    except httpx.TimeoutException:
        return ErrorResponseModel(
            status="error", message="Validation request timed out"
        )
    except Exception as e:
        return ErrorResponseModel(
            status="error", message=f"Error validating API key: {str(e)}"
        )


@ai_router.post("/assess-plagiarism", response_model=ResponseModel)
@verify_admin_or_institution
async def assess_plagiarism_endpoint(
    request: PlagiarismRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Run plagiarism + AI-generation assessment against a team's submission history."""
    try:
        institution_id, is_admin = _resolve_institution(current_user)
        if not institution_id:
            return ErrorResponseModel(
                status="error", message="Institution ID not found in token"
            )

        # Verify caller owns this league (admin bypasses ownership check).
        try:
            league = get_league_by_id(
                session, request.league_id, institution_id, is_admin=is_admin
            )
        except LeagueNotFoundError:
            return ErrorResponseModel(
                status="error", message=f"League {request.league_id} not found"
            )
        except InstitutionAccessError:
            return ErrorResponseModel(
                status="error",
                message="You don't have permission to access this league",
            )

        # Verify the team exists and belongs to that league.
        team = get_team_in_league(session, request.team_name, request.league_id)
        if not team:
            return ErrorResponseModel(
                status="error",
                message=(
                    f"Team '{request.team_name}' not found in league "
                    f"{request.league_id}"
                ),
            )

        # Audit log.
        logger.info(
            "Plagiarism assessment: caller=%s role=%s team=%s league_id=%s",
            current_user.get("team_name"),
            current_user.get("role"),
            team.name,
            request.league_id,
        )

        report = await assess_team_for_plagiarism(
            session, team, request.league_id, game_name=league.game
        )
        return ResponseModel(
            status="success",
            message="Assessment complete",
            data=report.model_dump(),
        )
    except NoApiKeyError as e:
        return ErrorResponseModel(status="error", message=str(e))
    except NoSubmissionsError as e:
        return ErrorResponseModel(status="error", message=str(e))
    except PayloadTooLargeError as e:
        return ErrorResponseModel(status="error", message=str(e))
    except LLMResponseError as e:
        logger.error("LLM response error in plagiarism assessment: %s", e)
        return ErrorResponseModel(
            status="error",
            message=f"AI provider returned malformed response: {e}",
        )
    except httpx.TimeoutException:
        return ErrorResponseModel(
            status="error", message="AI provider request timed out"
        )
    except Exception as e:
        logger.exception("Unexpected error in plagiarism assessment")
        return ErrorResponseModel(
            status="error", message=f"Internal error: {str(e)}"
        )
