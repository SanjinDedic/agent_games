import time
from datetime import timedelta

from sqlmodel import Session

from backend.database.db_models import (
    Admin,
    Institution,
    League,
    Team,
)
from backend.tests.conftest import TEST_PASSWORD_HASHES, create_test_institution
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


def test_admin_login_success(client, db_session: Session):
    """Test successful admin login scenarios"""

    # Test case 1: Basic admin login
    admin = Admin(
        username="test_admin", password_hash=TEST_PASSWORD_HASHES["test_password"]
    )
    db_session.add(admin)
    db_session.commit()

    response = client.post(
        "/auth/admin-login",
        json={"username": "test_admin", "password": "test_password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Test case 2: Login with different admin
    admin2 = Admin(username="admin2", password_hash=TEST_PASSWORD_HASHES["password2"])
    db_session.add(admin2)
    db_session.commit()

    response = client.post(
        "/auth/admin-login", json={"username": "admin2", "password": "password2"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_admin_login_exceptions(client, db_session: Session):
    """Test error cases for admin login"""

    # Create test admin
    admin = Admin(
        username="test_admin", password_hash=TEST_PASSWORD_HASHES["test_password"]
    )
    db_session.add(admin)
    db_session.commit()

    # Test case 1: Non-existent admin
    response = client.post(
        "/auth/admin-login",
        json={"username": "non_existent", "password": "test_password"},
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

    # Test case 2: Wrong password
    response = client.post(
        "/auth/admin-login",
        json={"username": "test_admin", "password": "wrong_password"},
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

    # Test case 3: Missing username
    response = client.post("/auth/admin-login", json={"password": "test_password"})
    assert response.status_code == 422

    # Test case 4: Missing password
    response = client.post("/auth/admin-login", json={"username": "test_admin"})
    assert response.status_code == 422

    # Test case 5: Empty credentials
    response = client.post("/auth/admin-login", json={"username": "", "password": ""})
    assert response.status_code == 422


def test_team_login_success(client, db_session: Session):
    """Test successful team login scenarios"""

    # First create a league for the teams
    league = League(
        name="test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()

    # Test case 1: Basic team login
    team = Team(
        name="test_team",
        school_name="Test School",
        password_hash=TEST_PASSWORD_HASHES["team_password"],
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()

    response = client.post(
        "/auth/team-login", json={"name": "test_team", "password": "team_password"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Test case 2: Login with different team
    team2 = Team(
        name="team2",
        school_name="School 2",
        password_hash=TEST_PASSWORD_HASHES["password2"],
        league_id=league.id,
    )
    db_session.add(team2)
    db_session.commit()

    response = client.post(
        "/auth/team-login", json={"name": "team2", "password": "password2"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_team_login_duplicate_name_across_institutions(client, db_session: Session):
    """Two teams in different institutions can share a name; login matches on
    name + password and authenticates the one whose password verifies."""
    now = utc_now()
    inst_a = create_test_institution(
        session=db_session, name="login_inst_a", password_hash="hash"
    )
    inst_b = create_test_institution(
        session=db_session, name="login_inst_b", password_hash="hash"
    )

    leagues = {}
    for key, inst in (("a", inst_a), ("b", inst_b)):
        league = League(
            name=f"dup_login_league_{key}",
            created_date=now,
            expiry_date=now + timedelta(days=7),
            game="greedy_pig",
            institution_id=inst.id,
        )
        db_session.add(league)
        db_session.commit()
        db_session.refresh(league)
        leagues[key] = league

    # Same name in both institutions, but different passwords.
    team_a = Team(
        name="shared_login_name",
        school_name="A",
        password_hash=TEST_PASSWORD_HASHES["team_password"],
        league_id=leagues["a"].id,
        institution_id=inst_a.id,
    )
    team_b = Team(
        name="shared_login_name",
        school_name="B",
        password_hash=TEST_PASSWORD_HASHES["password2"],
        league_id=leagues["b"].id,
        institution_id=inst_b.id,
    )
    db_session.add(team_a)
    db_session.add(team_b)
    db_session.commit()
    db_session.refresh(team_a)
    db_session.refresh(team_b)

    # Each password logs in the corresponding team (would raise
    # MultipleResultsFound under the old global-unique .one_or_none() lookup).
    resp_a = client.post(
        "/auth/team-login",
        json={"name": "shared_login_name", "password": "team_password"},
    )
    assert resp_a.status_code == 200

    resp_b = client.post(
        "/auth/team-login",
        json={"name": "shared_login_name", "password": "password2"},
    )
    assert resp_b.status_code == 200

    # The tokens resolve to the two distinct teams.
    from jose import jwt

    from backend.routes.auth.auth_config import ALGORITHM, SECRET_KEY

    payload_a = jwt.decode(
        resp_a.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM]
    )
    payload_b = jwt.decode(
        resp_b.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM]
    )
    assert payload_a["team_id"] == team_a.id
    assert payload_b["team_id"] == team_b.id

    # A password that matches neither team fails cleanly.
    resp_bad = client.post(
        "/auth/team-login",
        json={"name": "shared_login_name", "password": "definitely_wrong"},
    )
    assert resp_bad.status_code == 401
    assert "Invalid team password" in resp_bad.json()["detail"]


def test_team_login_exceptions(client, db_session: Session):
    """Test error cases for team login"""

    # Create a test league and team
    league = League(
        name="test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()

    team = Team(
        name="test_team",
        school_name="Test School",
        password_hash=TEST_PASSWORD_HASHES["team_password"],
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()

    # Test case 1: Non-existent team
    response = client.post(
        "/auth/team-login", json={"name": "non_existent", "password": "team_password"}
    )
    assert response.status_code == 401
    assert "not found" in response.json()["detail"].lower()

    # Test case 2: Wrong password
    response = client.post(
        "/auth/team-login", json={"name": "test_team", "password": "wrong_password"}
    )
    assert response.status_code == 401
    assert "Invalid team password" in response.json()["detail"]

    # Test case 3: Missing team name
    response = client.post("/auth/team-login", json={"password": "team_password"})
    assert response.status_code == 422

    # Test case 4: Missing password
    response = client.post("/auth/team-login", json={"name": "test_team"})
    assert response.status_code == 422

    # Test case 5: Empty credentials
    response = client.post("/auth/team-login", json={"name": "", "password": ""})
    assert response.status_code == 422

    # Test case 6: Malformed JSON
    response = client.post("/auth/team-login", data="invalid json")
    assert response.status_code == 422


def test_token_validation(client, db_session: Session):
    """Test token validation and expiry"""

    # Create timezone object
    
    # Create test institution with timezone-aware datetimes
    institution = create_test_institution(
        db_session,
        name="test_institution",
        contact_person="Test Contact",
        created_date=utc_now(),  # Add timezone
        subscription_expiry=utc_now()
        + timedelta(days=30),  # Add timezone
        password_hash=TEST_PASSWORD_HASHES["inst_password"],
    )

    # Get institution token
    response = client.post(
        "/auth/institution-login",
        json={"name": "test_institution", "password": "inst_password"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Test valid token with institution endpoint
    response = client.get(
        "/institution/get-all-teams", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    # Create token that is already expired
    expired_token = create_access_token(
        data={
            "sub": "test_institution",
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(microseconds=1),
    )
    # Wait to ensure token is expired
    time.sleep(0.1)

    response = client.get(
        "/institution/get-all-teams",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401

    # Test invalid token format
    response = client.get(
        "/institution/get-all-teams", headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

    # Test missing token
    response = client.get("/institution/get-all-teams")
    assert response.status_code == 401


def test_team_login_is_teacher_claim(client, db_session: Session):
    """Team tokens carry is_teacher from the owning institution"""
    teacher_inst = create_test_institution(
        db_session,
        name="teacher_claim_inst",
        password_hash=TEST_PASSWORD_HASHES["inst_password"],
        is_teacher=True,
    )
    plain_inst = create_test_institution(
        db_session,
        name="plain_claim_inst",
        password_hash=TEST_PASSWORD_HASHES["inst_password"],
    )

    now = utc_now()
    teams = {}
    for key, inst in (("teacher", teacher_inst), ("plain", plain_inst)):
        league = League(
            name=f"{key}_claim_league",
            created_date=now,
            expiry_date=now + timedelta(days=7),
            game="greedy_pig",
            institution_id=inst.id,
        )
        db_session.add(league)
        db_session.commit()
        db_session.refresh(league)
        team = Team(
            name=f"{key}_claim_student",
            school_name=inst.name,
            password_hash=TEST_PASSWORD_HASHES["team_password"],
            league_id=league.id,
            institution_id=inst.id,
        )
        db_session.add(team)
        db_session.commit()
        teams[key] = team

    from jose import jwt

    from backend.routes.auth.auth_config import ALGORITHM, SECRET_KEY

    for key, expected in (("teacher", True), ("plain", False)):
        response = client.post(
            "/auth/team-login",
            json={"name": teams[key].name, "password": "team_password"},
        )
        assert response.status_code == 200
        payload = jwt.decode(
            response.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM]
        )
        assert payload["is_teacher"] is expected
