import time
from datetime import datetime, timedelta

import pytest
from sqlmodel import Session

from backend.database.db_models import Institution, get_password_hash
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def test_institution(db_session: Session):
    """Create a test institution for login tests"""
    # Create with naive datetime to avoid timezone comparison issues
    institution = Institution(
        name="test_institution",
        contact_person="Test Contact",
        contact_email="test@example.com",
        created_date=datetime.now(),  # Using naive datetime
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),  # Using naive datetime
        docker_access=True,
    )
    institution.set_password("inst_password")
    
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)
    
    return institution


@pytest.fixture
def expired_institution(db_session: Session):
    """Create an institution with an expired subscription"""
    institution = Institution(
        name="expired_institution",
        contact_person="Expired Contact",
        contact_email="expired@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() - timedelta(days=1),  # Expired
        docker_access=True,
    )
    institution.set_password("expired_password")
    
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)
    
    return institution


@pytest.fixture
def inactive_institution(db_session: Session):
    """Create an institution with an inactive subscription"""
    institution = Institution(
        name="inactive_institution",
        contact_person="Inactive Contact",
        contact_email="inactive@example.com",
        created_date=datetime.now(),
        subscription_active=False,  # Inactive
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
    )
    institution.set_password("inactive_password")
    
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)
    
    return institution


def test_institution_login_success(client, test_institution):
    """Test successful institution login"""
    # Test basic login
    response = client.post(
        "/auth/institution-login",
        json={"name": "test_institution", "password": "inst_password"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"
    
    # Verify token works with an institution endpoint
    token = data["data"]["access_token"]
    response = client.get(
        "/institution/get-all-teams",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_institution_login_failures(client, test_institution, expired_institution, inactive_institution):
    """Test various institution login failure cases"""
    
    # Test case 1: Non-existent institution
    response = client.post(
        "/auth/institution-login",
        json={"name": "non_existent", "password": "inst_password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "not found" in data["message"].lower()
    
    # Test case 2: Wrong password
    response = client.post(
        "/auth/institution-login",
        json={"name": "test_institution", "password": "wrong_password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "invalid password" in data["message"].lower()
    
    # Test case 3: Missing name
    response = client.post(
        "/auth/institution-login",
        json={"password": "inst_password"},
    )
    assert response.status_code == 422
    
    # Test case 4: Missing password
    response = client.post(
        "/auth/institution-login",
        json={"name": "test_institution"},
    )
    assert response.status_code == 422
    
    # Test case 5: Empty credentials
    response = client.post(
        "/auth/institution-login",
        json={"name": "", "password": ""},
    )
    assert response.status_code == 422
    
    # Test case 6: Expired subscription
    response = client.post(
        "/auth/institution-login",
        json={"name": "expired_institution", "password": "expired_password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "expired" in data["message"].lower()
    
    # Test case 7: Inactive subscription
    response = client.post(
        "/auth/institution-login",
        json={"name": "inactive_institution", "password": "inactive_password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "not active" in data["message"].lower()


def test_token_expiration(client, test_institution):
    """Test institution token expiration"""
    # Create a short-lived token
    token = create_access_token(
        data={
            "sub": test_institution.name,
            "role": "institution",
            "institution_id": test_institution.id,
        },
        expires_delta=timedelta(microseconds=100),  # Very short expiration
    )

    # Wait for token to expire
    time.sleep(0.5)

    # Try to use expired token
    response = client.get(
        "/institution/get-all-teams",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()
