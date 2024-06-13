# tests/test_database.py

import os
import sys
import pytest
from sqlmodel import Session, select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models_db import Admin
from database import create_administrator, get_db_engine
from tests.database_setup import setup_test_db

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    setup_test_db()

@pytest.fixture(scope="function")
def db_session():
    engine = get_db_engine()
    with Session(engine) as session:
        yield session
        session.rollback()

def test_create_administrator(db_session):
    result = create_administrator(db_session, 'admin', 'password123')
    assert result == {"status": "success", "message": "Admin 'admin' created successfully"}
    
    administrator = db_session.exec(select(Admin).where(Admin.username == 'admin')).one_or_none()
    assert administrator is not None
    assert administrator.username == 'admin'

def test_create_administrator_missing_fields(db_session):
    result = create_administrator(db_session, 'admin', '')
    assert result == {"status": "failed", "message": "Username and password are required"}
    
    administrator = db_session.exec(select(Admin).where(Admin.username == 'admin')).one_or_none()
    assert administrator is None

def test_create_administrator_duplicate(db_session):
    create_administrator(db_session, 'Administrator', 'BOSSMAN')
    result = create_administrator(db_session, 'Administrator', 'BOSSMAN')
    assert result == {"status": "failed", "message": "Admin with username 'Administrator' already exists"}