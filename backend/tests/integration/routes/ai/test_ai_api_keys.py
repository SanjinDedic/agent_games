from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.routes.ai.ai_db import mask_key
from backend.routes.auth.auth_core import create_access_token


# --- Unit tests for mask_key ---


def test_mask_key_normal():
    assert mask_key("sk-1234567890abcdef") == "sk-1****cdef"


def test_mask_key_short():
    assert mask_key("12345678") == "****"


def test_mask_key_empty():
    assert mask_key("") == ""


def test_mask_key_none():
    assert mask_key(None) == ""


def test_mask_key_exactly_nine_chars():
    assert mask_key("123456789") == "1234****6789"


# --- Integration tests for GET /ai/api-keys ---


def test_get_api_keys_empty(client, auth_headers):
    """Initially no keys are configured"""
    response = client.get("/ai/api-keys", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["openai_api_key"] == ""


def test_get_api_keys_unauthenticated(client):
    """No token returns 401"""
    response = client.get("/ai/api-keys")
    assert response.status_code == 401


def test_get_api_keys_wrong_role(client):
    """Non-admin role returns 403"""
    token = create_access_token(
        data={"sub": "student_user", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        "/ai/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# --- Integration tests for POST /ai/api-keys ---


def test_update_api_key(client, auth_headers):
    """Update OpenAI key and verify masked response"""
    response = client.post(
        "/ai/api-keys",
        headers=auth_headers,
        json={"openai_api_key": "sk-test1234567890abcdef"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["openai_api_key"] == "sk-t****cdef"


def test_update_then_get_api_key(client, auth_headers):
    """Key persists after update"""
    client.post(
        "/ai/api-keys",
        headers=auth_headers,
        json={"openai_api_key": "sk-test1234567890abcdef"},
    )
    response = client.get("/ai/api-keys", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["openai_api_key"] == "sk-t****cdef"


def test_update_api_key_overwrite(client, auth_headers):
    """Updating an existing key overwrites it"""
    client.post(
        "/ai/api-keys",
        headers=auth_headers,
        json={"openai_api_key": "sk-first000000000000000"},
    )
    response = client.post(
        "/ai/api-keys",
        headers=auth_headers,
        json={"openai_api_key": "sk-second00000000000000"},
    )
    assert response.json()["data"]["openai_api_key"] == "sk-s****0000"


def test_update_api_key_none_no_change(client, auth_headers):
    """Sending None for a key does not change it"""
    client.post(
        "/ai/api-keys",
        headers=auth_headers,
        json={"openai_api_key": "sk-test1234567890abcdef"},
    )
    response = client.post(
        "/ai/api-keys",
        headers=auth_headers,
        json={},  # openai_api_key defaults to None
    )
    assert response.json()["data"]["openai_api_key"] == "sk-t****cdef"


def test_update_api_key_unauthenticated(client):
    """No token returns 401"""
    response = client.post(
        "/ai/api-keys",
        json={"openai_api_key": "sk-test"},
    )
    assert response.status_code == 401


# --- Integration tests for POST /ai/api-keys/validate ---


def test_validate_no_stored_key(client, auth_headers):
    """Validate with no stored key and no key in request"""
    response = client.post(
        "/ai/api-keys/validate",
        headers=auth_headers,
        json={"provider": "openai"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["valid"] is False
    assert "no api key configured" in data["message"].lower()


def test_validate_unknown_provider(client, auth_headers):
    """Unknown provider returns error"""
    response = client.post(
        "/ai/api-keys/validate",
        headers=auth_headers,
        json={"provider": "unknown_provider", "api_key": "some-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "unknown provider" in data["message"].lower()


@patch("backend.routes.ai.ai_router.httpx.AsyncClient")
def test_validate_valid_key(mock_client_cls, client, auth_headers):
    """Valid key returns valid=True"""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    response = client.post(
        "/ai/api-keys/validate",
        headers=auth_headers,
        json={"provider": "openai", "api_key": "sk-valid-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["valid"] is True


@patch("backend.routes.ai.ai_router.httpx.AsyncClient")
def test_validate_invalid_key(mock_client_cls, client, auth_headers):
    """Invalid key returns valid=False"""
    mock_response = MagicMock()
    mock_response.status_code = 401

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    response = client.post(
        "/ai/api-keys/validate",
        headers=auth_headers,
        json={"provider": "openai", "api_key": "sk-invalid-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["valid"] is False


@patch("backend.routes.ai.ai_router.httpx.AsyncClient")
def test_validate_stored_key(mock_client_cls, client, auth_headers):
    """Validate the stored key when no key provided in request"""
    # First store a key
    client.post(
        "/ai/api-keys",
        headers=auth_headers,
        json={"openai_api_key": "sk-stored-key-12345678"},
    )

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    response = client.post(
        "/ai/api-keys/validate",
        headers=auth_headers,
        json={"provider": "openai"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["valid"] is True

    # Verify the correct key was used in the request
    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    assert call_args[1]["headers"]["Authorization"] == "Bearer sk-stored-key-12345678"


@patch("backend.routes.ai.ai_router.httpx.AsyncClient")
def test_validate_timeout(mock_client_cls, client, auth_headers):
    """Timeout returns error"""
    import httpx

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    response = client.post(
        "/ai/api-keys/validate",
        headers=auth_headers,
        json={"provider": "openai", "api_key": "sk-some-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "timed out" in data["message"].lower()
