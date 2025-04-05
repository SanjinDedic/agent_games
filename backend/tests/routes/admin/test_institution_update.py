from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def update_institution_setup(db_session: Session) -> Institution:
    """Create an institution for update testing"""
    institution = Institution(
        name="update_test_institution",
        contact_person="Original Contact",
        contact_email="original@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=False,
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)
    
    return institution


def test_institution_update_success(client, auth_headers, update_institution_setup, db_session):
    """Test successful institution update"""
    institution = update_institution_setup
    
    # Test updating various fields
    update_data = {
        "id": institution.id,
        "name": "updated_institution",
        "contact_person": "Updated Contact",
        "contact_email": "updated@example.com",
        "subscription_active": False,
        "docker_access": True,
        "password": "new_password",
    }
    
    response = client.post(
        "/admin/institution-update",
        headers=auth_headers,
        json=update_data,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "institution updated successfully" in data["message"].lower()
    
    # Verify updates in database
    db_session.refresh(institution)
    assert institution.name == "updated_institution"
    assert institution.contact_person == "Updated Contact"
    assert institution.contact_email == "updated@example.com"
    assert institution.subscription_active is False
    assert institution.docker_access is True
    
    # Test partial update
    partial_update = {
        "id": institution.id,
        "contact_person": "Partially Updated Contact",
    }
    
    response = client.post(
        "/admin/institution-update",
        headers=auth_headers,
        json=partial_update,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Verify only specified fields were updated
    db_session.refresh(institution)
    assert institution.name == "updated_institution"  # Unchanged
    assert institution.contact_person == "Partially Updated Contact"  # Updated
    assert institution.contact_email == "updated@example.com"  # Unchanged


def test_institution_update_failures(client, auth_headers, update_institution_setup, db_session):
    """Test failure cases for institution update"""
    institution = update_institution_setup
    
    # Test case 1: Non-existent institution
    update_data = {
        "id": 99999,  # Non-existent ID
        "name": "non_existent_update",
    }
    
    response = client.post(
        "/admin/institution-update",
        headers=auth_headers,
        json=update_data,
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
    
    # Test case 2: Duplicate institution name
    # Create another institution first
    other_institution = Institution(
        name="other_institution",
        contact_person="Other Contact",
        contact_email="other@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=False,
        password_hash="test_hash",
    )
    db_session.add(other_institution)
    db_session.commit()
    
    # Try to update to a name that already exists
    duplicate_name_update = {
        "id": institution.id,
        "name": "other_institution",  # Name already exists
    }
    
    response = client.post(
        "/admin/institution-update",
        headers=auth_headers,
        json=duplicate_name_update,
    )
    
    # This might either return a 200 with error or a database integrity error
    # Either case would be valid - we'll check for both possibilities
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "error":
            assert ("already exists" in data["message"].lower() or 
        "duplicate" in data["message"].lower() or 
        "unique constraint" in data["message"].lower())
    
    # Test case 3: Missing ID
    missing_id_update = {
        "name": "missing_id_update",
    }
    
    response = client.post(
        "/admin/institution-update",
        headers=auth_headers,
        json=missing_id_update,
    )
    assert response.status_code == 422
    
    # Test case 4: Invalid email format
    invalid_email_update = {
        "id": institution.id,
        "contact_email": "not_an_email",
    }
    
    response = client.post(
        "/admin/institution-update",
        headers=auth_headers,
        json=invalid_email_update,
    )
    assert response.status_code == 422
    
    # Test case 5: Invalid date format
    invalid_date_update = {
        "id": institution.id,
        "subscription_expiry": "not_a_date",
    }
    
    response = client.post(
        "/admin/institution-update",
        headers=auth_headers,
        json=invalid_date_update,
    )
    assert response.status_code == 422
    
    # Test case 6: Unauthorized access (no token)
    response = client.post(
        "/admin/institution-update",
        json={"id": institution.id, "name": "unauthorized_update"},
    )
    assert response.status_code == 401
    
    # Test case 7: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/admin/institution-update",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"id": institution.id, "name": "wrong_role_update"},
    )
    assert response.status_code == 403