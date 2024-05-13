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

def test_league_creation(client: TestClient):
    response = client.post("/league_create", json={"name": "week1"})
    assert response.status_code == 200
    assert response.json() == {"status" : "success", "link": "MQ=="}

    response = client.post("/league_create")
    assert response.status_code == 422
    
    response = client.post("/league_create", json={"name": ""})
    assert response.status_code == 200
    assert response.json() == {"status" : "failed", "message": "Name is Empty"}
