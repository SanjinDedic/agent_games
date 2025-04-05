from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution, League
from backend.routes.auth.auth_core import create_access_token


def test_institution_create_success(client, auth_headers, db_session):
    """Test successful institution creation"""
    # Create a new institution
    institution_data = {
        "name": "new_institution",
        "contact_person": "New Contact",
        "contact_email": "new@example.com",
        "password": "new_password",
        "subscription_expiry": (datetime.now() + timedelta(days=30)).isoformat(),
        "docker_access": True,
    }
    
    response = client.post(
        "/admin/institution-create",
        headers=auth_headers,
        json=institution_data,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "institution created successfully" in data["message"].lower()
    assert "id" in data["data"]
    
    # Verify institution was created in database
    institution = db_session.exec(
        select(Institution).where(Institution.name == "new_institution")
    ).first()
    assert institution is not None
    assert institution.contact_person == "New Contact"
    assert institution.contact_email == "new@example.com"
    assert institution.docker_access is True
    
    # Verify unassigned league was created
    unassigned_league = db_session.exec(
        select(League)
        .where(League.name == "unassigned")
        .where(League.institution_id == institution.id)
    ).first()
    assert unassigned_league is not None


def test_institution_create_failures(client, auth_headers, db_session):
    """Test failure cases for institution creation"""
    # Create an existing institution first
    existing_institution = Institution(
        name="existing_institution",
        contact_person="Existing Contact",
        contact_email="existing@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(existing_institution)
    db_session.commit()
    
    # Test case 1: Duplicate institution name
    institution_data = {
        "name": "existing_institution",  # Same name as existing institution
        "contact_person": "New Contact",
        "contact_email": "new@example.com",
        "password": "new_password",
        "subscription_expiry": (datetime.now() + timedelta(days=30)).isoformat(),
        "docker_access": True,
    }
    
    response = client.post(
        "/admin/institution-create",
        headers=auth_headers,
        json=institution_data,
    )
    assert response.status_code == 200  # API returns 200 with error status
    data = response.json()
    assert data["status"] == "error"
    assert "already exists" in data["message"].lower()
    
    # Test case 2: Missing required fields
    incomplete_data = {
        "name": "incomplete_institution",
        # Missing contact_person, contact_email, password
        "subscription_expiry": (datetime.now() + timedelta(days=30)).isoformat(),
    }
    
    response = client.post(
        "/admin/institution-create",
        headers=auth_headers,
        json=incomplete_data,
    )
    assert response.status_code == 422
    
    # Test case 3: Invalid field types
    invalid_data = {
        "name": "invalid_institution",
        "contact_person": "Invalid Contact",
        "contact_email": "not_an_email",  # Invalid email format
        "password": "password",
        "subscription_expiry": (datetime.now() + timedelta(days=30)).isoformat(),
        "docker_access": True,
    }
    
    response = client.post(
        "/admin/institution-create",
        headers=auth_headers,
        json=invalid_data,
    )
    assert response.status_code == 422
    
    # Test case 4: Empty institution name
    empty_name_data = {
        "name": "",  # Empty name
        "contact_person": "Empty Name Contact",
        "contact_email": "empty@example.com",
        "password": "password",
        "subscription_expiry": (datetime.now() + timedelta(days=30)).isoformat(),
        "docker_access": True,
    }
    
    response = client.post(
        "/admin/institution-create",
        headers=auth_headers,
        json=empty_name_data,
    )
    assert response.status_code == 422
    
    # Test case 5: Unauthorized access (no token)
    response = client.post(
        "/admin/institution-create",
        json=institution_data,
    )
    assert response.status_code == 401
    
    # Test case 6: Wrong role token
    wrong_token = create_access_token(
        data={"sub": "wrong", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/admin/institution-create",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json=institution_data,
    )
    assert response.status_code == 403