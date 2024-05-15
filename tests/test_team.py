from fastapi.testclient import TestClient
import os,sys
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api import app
from database import get_db_session
import pytest

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")  
def client_fixture(session: Session):  
    def get_session_override():  
        return session

    app.dependency_overrides[get_db_session] = get_session_override  

    client = TestClient(app)  
    yield client  
    app.dependency_overrides.clear()


def test_team_login(client: TestClient):
    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"})
    assert response.status_code == 200
    assert "access_token" in response.json()

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "No team found with these credentials"}

    response = client.post("/team_login", json={"team": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": ""})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": "  ", "password": "ighEMkOP"})
    assert response.status_code == 422