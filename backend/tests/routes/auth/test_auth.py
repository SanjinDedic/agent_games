import time
from datetime import datetime, timedelta

from sqlmodel import Session, select

from backend.database.db_models import Admin, League, Team, get_password_hash
from backend.routes.auth.auth_core import create_access_token


def test_admin_login_success(client, db_session: Session):
    """Test successful admin login scenarios"""

    # Test case 1: Basic admin login
    admin = Admin(
        username="test_admin", password_hash=get_password_hash("test_password")
    )
    db_session.add(admin)
    db_session.commit()

    response = client.post(
        "/auth/admin-login",
        json={"username": "test_admin", "password": "test_password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"

    # Test case 2: Login with different admin
    admin2 = Admin(username="admin2", password_hash=get_password_hash("password2"))
    db_session.add(admin2)
    db_session.commit()

    response = client.post(
        "/auth/admin-login", json={"username": "admin2", "password": "password2"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data["data"]


def test_admin_login_exceptions(client, db_session: Session):
    """Test error cases for admin login"""

    # Create test admin
    admin = Admin(
        username="test_admin", password_hash=get_password_hash("test_password")
    )
    db_session.add(admin)
    db_session.commit()

    # Test case 1: Non-existent admin
    response = client.post(
        "/auth/admin-login",
        json={"username": "non_existent", "password": "test_password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "Invalid credentials" in data["message"]

    # Test case 2: Wrong password
    response = client.post(
        "/auth/admin-login",
        json={"username": "test_admin", "password": "wrong_password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "Invalid credentials" in data["message"]

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
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()

    # Test case 1: Basic team login
    team = Team(
        name="test_team",
        school_name="Test School",
        password_hash=get_password_hash("team_password"),
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()

    response = client.post(
        "/auth/team-login", json={"name": "test_team", "password": "team_password"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"

    # Test case 2: Login with different team
    team2 = Team(
        name="team2",
        school_name="School 2",
        password_hash=get_password_hash("password2"),
        league_id=league.id,
    )
    db_session.add(team2)
    db_session.commit()

    response = client.post(
        "/auth/team-login", json={"name": "team2", "password": "password2"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data["data"]


def test_team_login_exceptions(client, db_session: Session):
    """Test error cases for team login"""

    # Create a test league and team
    league = League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()

    team = Team(
        name="test_team",
        school_name="Test School",
        password_hash=get_password_hash("team_password"),
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()

    # Test case 1: Non-existent team
    response = client.post(
        "/auth/team-login", json={"name": "non_existent", "password": "team_password"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "not found" in data["message"].lower()

    # Test case 2: Wrong password
    response = client.post(
        "/auth/team-login", json={"name": "test_team", "password": "wrong_password"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "Invalid team password" in data["message"]

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

    # Create test admin
    admin = Admin(
        username="test_admin", password_hash=get_password_hash("test_password")
    )
    db_session.add(admin)
    db_session.commit()

    # Get valid token
    response = client.post(
        "/auth/admin-login",
        json={"username": "test_admin", "password": "test_password"},
    )
    token = response.json()["data"]["access_token"]

    # Test valid token with admin endpoint
    response = client.get(
        "/admin/get-all-teams", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    # Create token that is already expired
    expired_token = create_access_token(
        data={"sub": "admin", "role": "admin"}, expires_delta=timedelta(microseconds=1)
    )
    # Wait to ensure token is expired
    time.sleep(0.1)

    response = client.get(
        "/admin/get-all-teams", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "token has expired" in data["detail"].lower()

    # Test invalid token format
    response = client.get(
        "/admin/get-all-teams", headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

    # Test missing token
    response = client.get("/admin/get-all-teams")
    assert response.status_code == 401
