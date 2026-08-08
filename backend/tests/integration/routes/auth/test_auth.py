"""Tests for the unified login surface: POST /auth/setup, /auth/login and
/auth/agent-login."""

from datetime import timedelta

from jose import jwt
from sqlmodel import Session, select

from backend.database.db_models import AgentAPIKey, League, Owner, Team, TeamType
from backend.routes.auth.auth_config import ALGORITHM, SECRET_KEY
from backend.routes.auth.auth_core import create_access_token
from backend.tests.conftest import TEST_PASSWORD_HASHES
from backend.time_utils import utc_now


def _claims(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# --- first-run setup -------------------------------------------------------


def test_setup_claims_an_unclaimed_deployment(client, db_session: Session):
    """The seeded test database has no owner, so setup succeeds and logs in."""
    response = client.post(
        "/auth/setup", json={"name": "the_teacher", "password": "a-good-password"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "owner"
    assert _claims(body["access_token"])["sub"] == "the_teacher"

    owner = db_session.exec(select(Owner)).one()
    assert owner.username == "the_teacher"
    assert owner.verify_password("a-good-password")


def test_setup_is_refused_once_an_owner_exists(client):
    """The one-shot check is the entire authorization for this endpoint."""
    first = client.post("/auth/setup", json={"name": "first", "password": "password1"})
    assert first.status_code == 200

    second = client.post("/auth/setup", json={"name": "second", "password": "password2"})
    assert second.status_code == 409
    assert "already been set up" in second.json()["detail"]


def test_setup_rejects_a_short_password(client):
    response = client.post("/auth/setup", json={"name": "someone", "password": "short"})
    assert response.status_code == 422


def test_config_reports_setup_required(client):
    """The frontend picks the setup form or the login form from this flag."""
    assert client.get("/config").json()["setup_required"] is True

    client.post("/auth/setup", json={"name": "owner", "password": "password123"})
    assert client.get("/config").json()["setup_required"] is False


# --- login -----------------------------------------------------------------


def test_login_as_owner(client, db_session: Session):
    owner = Owner(username="site_owner", password_hash=TEST_PASSWORD_HASHES["test_password"])
    db_session.add(owner)
    db_session.commit()

    response = client.post(
        "/auth/login", json={"name": "site_owner", "password": "test_password"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "owner"
    assert body["token_type"] == "bearer"

    claims = _claims(body["access_token"])
    assert claims["sub"] == "site_owner"
    assert claims["role"] == "owner"
    # Nothing tenancy-shaped survives in the token.
    assert "institution_id" not in claims
    assert "is_teacher" not in claims


def test_login_as_team(client, db_session: Session):
    """The same form authenticates a team, and says which role it got."""
    response = client.post("/auth/login", json={"name": "TeamA", "password": "AA"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "student"

    team = db_session.exec(select(Team).where(Team.name == "TeamA")).one()
    claims = _claims(body["access_token"])
    assert claims["sub"] == "TeamA"
    assert claims["role"] == "student"
    assert claims["team_id"] == team.id
    assert claims["league_id"] == team.league_id
    assert "institution_id" not in claims


def test_login_failures_are_indistinguishable(client, db_session: Session):
    """An unknown name and a wrong password must look identical, or the response
    reveals whether a name exists — and whether it is the owner's."""
    owner = Owner(username="site_owner", password_hash=TEST_PASSWORD_HASHES["test_password"])
    db_session.add(owner)
    db_session.commit()

    unknown = client.post("/auth/login", json={"name": "nobody", "password": "whatever"})
    wrong_owner_pw = client.post("/auth/login", json={"name": "site_owner", "password": "nope"})
    wrong_team_pw = client.post("/auth/login", json={"name": "TeamA", "password": "nope"})

    for response in (unknown, wrong_owner_pw, wrong_team_pw):
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"


def test_login_rejects_blank_fields(client):
    assert client.post("/auth/login", json={"name": "", "password": "x"}).status_code == 422
    assert client.post("/auth/login", json={"name": "x", "password": "  "}).status_code == 422
    assert client.post("/auth/login", json={"name": "x"}).status_code == 422


def test_login_resolves_one_team_per_name(client, db_session: Session):
    """Team names are globally unique, so login is a single-row lookup.

    Before this, names were unique only per institution and login had to try
    every match's password in turn — two teams sharing a name and a password
    were genuinely ambiguous.
    """
    league = db_session.exec(select(League).where(League.name == "greedy_pig_league")).one()
    duplicate = Team(
        name="TeamA",
        school_name="Somewhere Else",
        password_hash=TEST_PASSWORD_HASHES["password2"],
        league_id=league.id,
        team_type=TeamType.STUDENT,
    )
    db_session.add(duplicate)

    from sqlalchemy.exc import IntegrityError

    try:
        db_session.commit()
        raise AssertionError("a duplicate team name should violate the unique index")
    except IntegrityError:
        db_session.rollback()


# --- agent login -----------------------------------------------------------


def test_agent_login_with_api_key(client, db_session: Session):
    league = db_session.exec(select(League).where(League.name == "greedy_pig_league")).one()
    agent = Team(
        name="api_agent",
        school_name="AI Agent",
        league_id=league.id,
        team_type=TeamType.AGENT,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)

    db_session.add(AgentAPIKey(key="agent-key-123", team_id=agent.id))
    db_session.commit()

    response = client.post("/auth/agent-login", json={"api_key": "agent-key-123"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "ai_agent"
    assert _claims(body["access_token"])["role"] == "ai_agent"

    db_session.refresh(agent)
    assert agent.api_key.last_used is not None


def test_agent_login_rejects_unknown_key(client):
    response = client.post("/auth/agent-login", json={"api_key": "not-a-key"})
    assert response.status_code == 401


# --- token validation ------------------------------------------------------


def test_expired_token_is_rejected(client):
    expired = create_access_token(
        data={"sub": "test_owner", "role": "owner"},
        expires_delta=timedelta(minutes=-5),
    )
    response = client.get("/owner/get-all-teams", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_malformed_token_is_rejected(client):
    response = client.get(
        "/owner/get-all-teams", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert response.status_code == 401


def test_unknown_role_is_rejected(client):
    """get_current_user only accepts owner, student and ai_agent."""
    token = create_access_token(
        data={"sub": "whoever", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get("/owner/get-all-teams", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_hand_minted_service_token_is_rejected(client):
    """The service role used to be appended to every guard's allowed set, so a
    token like this passed every check including the admin-only ones. There is
    no service role now, and an unknown role fails closed."""
    token = create_access_token(
        data={"sub": "service", "role": "service"},
        expires_delta=timedelta(days=365),
    )
    response = client.get("/owner/get-all-teams", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_team_token_cannot_reach_owner_routes(client, team_headers):
    response = client.get("/owner/get-all-teams", headers=team_headers)
    assert response.status_code == 403


def test_owner_token_cannot_reach_team_routes(client, owner_headers):
    """require_team refuses a token with no team_id."""
    response = client.get("/user/get-team-submissions", headers=owner_headers)
    assert response.status_code == 403


def test_deleted_endpoints_are_gone(client):
    """The three separate login endpoints and the competition picker."""
    for path in ("/auth/admin-login", "/auth/institution-login", "/auth/team-login"):
        assert client.post(path, json={"name": "x", "password": "y"}).status_code == 404
    assert client.get("/auth/competitions").status_code == 404
