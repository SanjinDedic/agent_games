"""Integration tests for POST /auth/execution-token.

The endpoint exchanges any valid session token for a short-lived execution
token the browser presents directly to the fallback Lambda's Function URL.
Signed with the dedicated EXEC_JWT_SECRET — the Lambda-side stdlib verifier
(backend/fallback_lambda/exec_token.py) is used here to prove the minted
token is accepted end-to-end.
"""

import pytest

import backend.routes.auth.auth_config as auth_config
from backend.fallback_lambda import exec_token
from backend.routes.auth.auth_config import EXEC_TOKEN_EXPIRY_SECONDS

SECRET = "integration-exec-secret"


@pytest.fixture(autouse=True)
def exec_secret(monkeypatch):
    monkeypatch.setattr(auth_config, "EXEC_JWT_SECRET", SECRET)


def test_student_gets_verifiable_token(client, team_headers):
    response = client.post("/auth/execution-token", headers=team_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["expires_in"] == EXEC_TOKEN_EXPIRY_SECONDS

    claims = exec_token.verify(data["token"], SECRET)
    assert claims is not None
    assert claims["role"] == "student"
    assert claims["scope"] == "exec"


def test_admin_and_institution_get_tokens(
    client, admin_headers, institution_headers
):
    for headers, role in ((admin_headers, "admin"), (institution_headers, "institution")):
        response = client.post("/auth/execution-token", headers=headers)
        assert response.status_code == 200
        claims = exec_token.verify(response.json()["token"], SECRET)
        assert claims is not None and claims["role"] == role


def test_exec_token_is_not_a_session_token(client, team_headers):
    """An execution token must not open any API endpoint — different secret,
    and the exec scope means nothing to get_current_user."""
    token = client.post(
        "/auth/execution-token", headers=team_headers
    ).json()["token"]
    response = client.post(
        "/auth/execution-token", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_unauthenticated_is_401(client):
    assert client.post("/auth/execution-token").status_code == 401


def test_unconfigured_secret_is_503(client, team_headers, monkeypatch):
    monkeypatch.setattr(auth_config, "EXEC_JWT_SECRET", None)
    response = client.post("/auth/execution-token", headers=team_headers)
    assert response.status_code == 503
