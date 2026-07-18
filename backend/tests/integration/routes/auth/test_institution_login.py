import time
from datetime import timedelta

import pytest
from sqlmodel import Session

from backend.routes.auth.auth_core import create_access_token
from backend.tests.conftest import TEST_PASSWORD_HASHES, create_test_institution
from backend.time_utils import utc_now


@pytest.fixture
def test_institution(db_session: Session):
    """Create a test institution for login tests"""
    return create_test_institution(
        db_session,
        name="test_institution",
        contact_person="Test Contact",
        subscription_expiry=utc_now() + timedelta(days=30),
        password_hash=TEST_PASSWORD_HASHES["inst_password"],
    )


@pytest.fixture
def expired_institution(db_session: Session):
    """Create an institution with an expired subscription"""
    return create_test_institution(
        db_session,
        name="expired_institution",
        contact_person="Expired Contact",
        contact_email="expired@example.com",
        subscription_expiry=utc_now() - timedelta(days=1),  # Expired
        password_hash=TEST_PASSWORD_HASHES["expired_password"],
    )


@pytest.fixture
def inactive_institution(db_session: Session):
    """Create an institution with an inactive subscription"""
    return create_test_institution(
        db_session,
        name="inactive_institution",
        contact_person="Inactive Contact",
        contact_email="inactive@example.com",
        subscription_active=False,  # Inactive
        subscription_expiry=utc_now() + timedelta(days=30),
        password_hash=TEST_PASSWORD_HASHES["inactive_password"],
    )


def test_institution_login_success(client, test_institution):
    """Test successful institution login"""
    # Test basic login
    response = client.post(
        "/auth/institution-login",
        json={"name": "test_institution", "password": "inst_password"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify token works with an institution endpoint
    token = data["access_token"]
    response = client.get(
        "/institution/get-all-teams",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "teams" in response.json()


def test_institution_login_failures(client, test_institution, expired_institution, inactive_institution):
    """Test various institution login failure cases"""
    
    # Test case 1: Non-existent institution
    response = client.post(
        "/auth/institution-login",
        json={"name": "non_existent", "password": "inst_password"},
    )
    assert response.status_code == 401
    assert "not found" in response.json()["detail"].lower()

    # Test case 2: Wrong password
    response = client.post(
        "/auth/institution-login",
        json={"name": "test_institution", "password": "wrong_password"},
    )
    assert response.status_code == 401
    assert "invalid password" in response.json()["detail"].lower()
    
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
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()

    # Test case 7: Inactive subscription
    response = client.post(
        "/auth/institution-login",
        json={"name": "inactive_institution", "password": "inactive_password"},
    )
    assert response.status_code == 401
    assert "not active" in response.json()["detail"].lower()


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
    assert (
        "expired" in response.json()["detail"].lower()
        or "invalid" in response.json()["detail"].lower()
    )


def test_institution_login_is_teacher_claim(client, db_session, test_institution):
    """Institution tokens carry the is_teacher claim"""
    create_test_institution(
        db_session,
        name="teacher_institution",
        contact_person="Ms Smith",
        contact_email="smith@example.com",
        subscription_expiry=utc_now() + timedelta(days=30),
        password_hash=TEST_PASSWORD_HASHES["inst_password"],
        is_teacher=True,
    )

    from jose import jwt

    from backend.routes.auth.auth_config import ALGORITHM, SECRET_KEY

    response = client.post(
        "/auth/institution-login",
        json={"name": "teacher_institution", "password": "inst_password"},
    )
    assert response.status_code == 200
    payload = jwt.decode(
        response.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM]
    )
    assert payload["is_teacher"] is True

    response = client.post(
        "/auth/institution-login",
        json={"name": "test_institution", "password": "inst_password"},
    )
    assert response.status_code == 200
    payload = jwt.decode(
        response.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM]
    )
    assert payload["is_teacher"] is False
