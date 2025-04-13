from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def docker_access_setup(db_session: Session) -> Institution:
    """Create an institution for testing Docker access toggling"""
    # Create the institution with docker_access initially set to False
    institution = Institution(
        name="docker_test_institution",
        contact_person="Docker Test Contact",
        contact_email="docker@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=False,  # Initially False
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)
    
    return institution


def test_toggle_docker_access_success(client, auth_headers, docker_access_setup, db_session):
    """Test successful toggling of Docker access"""
    institution = docker_access_setup
    
    # Verify institution initially has docker_access=False
    assert institution.docker_access is False
    
    # Test enabling Docker access
    response = client.post(
        "/admin/toggle-docker-access",
        headers=auth_headers,
        json={"institution_id": institution.id, "enable": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "docker access enabled" in data["message"].lower()
    
    # Verify change in database
    db_session.refresh(institution)
    assert institution.docker_access is True
    
    # Test disabling Docker access
    response = client.post(
        "/admin/toggle-docker-access",
        headers=auth_headers,
        json={"institution_id": institution.id, "enable": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "docker access disabled" in data["message"].lower()
    
    # Verify change in database
    db_session.refresh(institution)
    assert institution.docker_access is False


def test_toggle_docker_access_failures(client, auth_headers, db_session):
    """Test failure cases for toggling Docker access"""
    # Test case 1: Non-existent institution
    response = client.post(
        "/admin/toggle-docker-access",
        headers=auth_headers,
        json={"institution_id": 99999, "enable": True},  # Non-existent ID
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 2: Missing institution_id
    response = client.post(
        "/admin/toggle-docker-access",
        headers=auth_headers,
        json={"enable": True},  # Missing institution_id
    )
    assert response.status_code == 422
    
    # Test case 3: Missing enable flag
    response = client.post(
        "/admin/toggle-docker-access",
        headers=auth_headers,
        json={"institution_id": 1},  # Missing enable flag
    )
    assert response.status_code == 422
    
    # Test case 4: Invalid institution_id type
    response = client.post(
        "/admin/toggle-docker-access",
        headers=auth_headers,
        json={"institution_id": "not_an_integer", "enable": True},
    )
    assert response.status_code == 422
    
    # Test case 5: Invalid enable type
    response = client.post(
        "/admin/toggle-docker-access",
        headers=auth_headers,
        json={"institution_id": 1, "enable": "not_a_boolean"},
    )
    assert response.status_code == 422
    
    # Test case 6: Unauthorized access (no token)
    response = client.post(
        "/admin/toggle-docker-access",
        json={"institution_id": 1, "enable": True},
    )
    assert response.status_code == 401
    
    # Test case 7: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/admin/toggle-docker-access",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"institution_id": 1, "enable": True},
    )
    assert response.status_code == 403