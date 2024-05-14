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

def test_get_token(client: TestClient):
    global ADMIN_VALID_TOKEN
    login_response = client.post("/admin_login", json={"password": "BOSSMAN"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    ADMIN_VALID_TOKEN = token

def test_league_creation(client: TestClient):
    response = client.post("/league_create", json={"name": "week1"})
    assert response.status_code == 200
    assert response.json() == {"status" : "success", "link": "MQ=="}

    response = client.post("/league_create")
    assert response.status_code == 422
    
    response = client.post("/league_create", json={"name": ""})
    assert response.status_code == 200
    assert response.json() == {"status" : "failed", "message": "Name is Empty"}

    response = client.post("/league_create", json={"name": "week2"}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert response.json() == {"status" : "success", "link": "Mg=="}



def test_league_join(client: TestClient):
    response = client.post("/league_join/MQ%3D%3D", json={"name": "std","password": "pass","school": "abc"})
    assert response.status_code == 200
    assert "access_token" in response.json()

    response = client.post("/league_join/MQ%3D%3D", json={"name": "std2","password": "passw","school": ""})
    assert response.status_code == 422

    response = client.post("/league_join/", json={"name": "std3","password": "passwo","school": "abc"})
    assert response.status_code == 404
    
    response = client.post("/league_join/MQ%3D%3D", json={"name": "std","password": "","school": "abc"})
    assert response.status_code == 422
    
    response = client.post("/league_join/MQ%3D%3D", json={"name": "","password": "pass","school": "abc"})
    assert response.status_code == 422
    
    response = client.post("/league_join/MQ%3D%3D", json={"name": "","password": "","school": "abc"})
    assert response.status_code == 422

    response = client.post("/league_join/MQ%3D%3D",json={"name": "std3","password": "passwo"})
    assert response.status_code == 422
    
    response = client.post("/league_join/MQ%3D%3D", json={"name": "std3","school": ""})
    assert response.status_code == 422
