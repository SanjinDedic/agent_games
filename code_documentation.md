# Project Sitemap

## /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games

[auth.py](/Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/auth.py)
### /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/auth.py
`
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from passlib.context import CryptContext

import base64


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now() + expires_delta if expires_delta else datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        team_name: str = payload.get("sub")
        user_role: str = payload.get("role")
        if team_name is None or user_role not in ["student", "admin"]:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"team_name": team_name, "role": user_role}

def encode_id(id: int) -> str:
    id_bytes = str(id).encode('utf-8')
    encoded_id = base64.urlsafe_b64encode(id_bytes).decode('utf-8')
    return encoded_id

def decode_id(encoded_id: str) -> int:
    id_bytes = base64.urlsafe_b64decode(encoded_id)
    id = int(id_bytes.decode('utf-8'))
    return id

`
## /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games

[config.py](/Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/config.py)
### /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/config.py
`
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
CURRENT_DIR = os.path.dirname(__file__)
CURRENT_DB = os.path.join(CURRENT_DIR, "teams.db")
GUEST_LEAGUE_EXPIRY = 24 #hours
ADMIN_LEAGUE_EXPIRY = 180 #1 week and 12 hours

def get_database_url():
    if os.environ.get("TESTING"):
        test_db_path = os.path.join(CURRENT_DIR, "test.db")  # Use a relative path for the test database
        return f"sqlite:///{test_db_path}"
        #Try an in memory db
        #return "sqlite:///:memory:"
    else:
        return f"sqlite:///{CURRENT_DB}"
`
## /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games

[database.py](/Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/database.py)
### /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/database.py
`
import logging
import json
import os
from datetime import datetime, timedelta
from sqlalchemy.exc import OperationalError
from sqlmodel import select, SQLModel
from config import CURRENT_DB, ACCESS_TOKEN_EXPIRE_MINUTES, get_database_url, GUEST_LEAGUE_EXPIRY 
from models import Admin, League, Team, Submission
from sqlalchemy import create_engine
from sqlmodel import Session, select
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    encode_id
)

def get_db_engine():
    return create_engine(get_database_url())

def create_database(engine, prnt=False):
    SQLModel.metadata.create_all(engine)
    
def print_database(engine):
    print("Database Tables:")
    for table in SQLModel.metadata.sorted_tables:
        print(f"\nTable: {table.name}")
        print("Columns:")
        for column in table.columns:
            print(f"- {column.name} ({column.type})")
        
        with engine.connect() as conn:
            result = conn.execute(select(table).limit(2)).fetchall()
            if result:
                print("First 2 rows of data:")
                for row in result:
                    print(row)
            else:
                print("No data available.")


def create_league(engine, league_name):
    try:
        with Session(engine) as session:
            league = League(
                name=league_name,
                created_date=datetime.now(),
                expiry_date=(datetime.now() + timedelta(hours=GUEST_LEAGUE_EXPIRY)),
                deleted_date=(datetime.now() + timedelta(days=7)),
                active=True,
                signup_link=None
            )
            session.add(league)
            session.flush()  # Flush to generate the league ID
            
            league.signup_link = encode_id(league.id)
            session.commit()
            
            return {"status": "success", "link": league.signup_link}
    except Exception as e:
        return {"status": "failed", "message": str(e)}


from sqlmodel import Session, select

def create_team(engine, league_link, name, password, school=None):
    try:
        with Session(engine) as session:
            print(f"Searching for league with signup link: {league_link}")  # Add this print statement
            league = session.exec(select(League).where(League.signup_link == league_link)).one_or_none()

            if league:
                print(f"League found: {league}")  # Add this print statement
                team = Team(name=name, school_name=school)
                team.set_password(password)
                session.add(team)
                team.league = league
                session.commit()

                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": name, "role": "student"},
                    expires_delta=access_token_expires
                )
                return {"access_token": access_token, "token_type": "bearer"}
            else:
                print(f"League '{league_link}' does not exist")
                return {"status": "failed", "message": f"League '{league_link}' does not exist"}
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {"status": "failed", "message": "Server error"}

def update_submission(engine, league_name, team_name, code):
    try:
        with engine.begin() as conn:
            league = conn.execute(select(League).where(League.name == league_name)).one_or_none()
            team = conn.execute(select(Team).where(Team.name == team_name, Team.league == league)).one_or_none()
            if league and team:
                submission = Submission(code=code, timestamp=datetime.now(), team=team, league=league)
                conn.add(submission)
            else:
                raise ValueError(f"Team '{team_name}' does not exist in league '{league_name}'")
    except Exception as e:
        raise e

def add_teams_from_json(engine, league_link, teams_json_path):
    try:
        with open(teams_json_path, 'r') as file:
            data = json.load(file)
            teams_list = data.get('teams', [])  # Use .get to safely handle missing 'teams' key

        for team_data in teams_list:
            # Check if all required fields are present in team_data
            required_fields = ["name", "password"]
            if not all(field in team_data for field in required_fields):
                raise ValueError("Invalid team data in JSON: missing required fields")

            create_result = create_team(engine, league_link, team_data["name"], team_data["password"], team_data.get("school", None))
            
            # Check for errors in team creation
            if create_result.get("status") == "failed":
                raise ValueError(f"Failed to create team '{team_data['name']}': {create_result['message']}")
            
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: 'teams_json_path' not found at: {teams_json_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Error: Invalid JSON format in '{teams_json_path}': {e}")
    except (ValueError, KeyError) as e:  # Catch specific errors for better messages
        raise ValueError(f"Error processing team data from JSON: {e}")

def get_team(engine, team_name, team_password):
    try:
        with Session(engine) as session:
            result = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
            if result and result.verify_password(team_password):  # Use the verify_password method
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": team_name, "role": "student"}, 
                    expires_delta=access_token_expires
                )
                return {"access_token": access_token, "token_type": "bearer"}
            else:
                return False
    except Exception as e:
        raise e

def get_admin(engine, username, password):
    print("GET ADMIN CALLED! with", username, password)

    try:
        with engine.connect() as conn:
            print("CONNECTION CREATED!")
            # Query the database for all users in the admin table
            admins = conn.execute(select(Admin)).fetchall()
            print(admins)

            # Query the database for the admin user with the given username
            admin = conn.execute(select(Admin).where(Admin.username == username)).one_or_none()
            if admin:
                print("ADMIN FOUND!")
                # Verifying the password
                if verify_password(password, admin.password_hash):
                    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                    access_token = create_access_token(
                        data={"sub": "admin", "role": "admin"},
                        expires_delta=access_token_expires
                    )
                    return {"access_token": access_token, "token_type": "bearer"}
                else:
                    print("INVALID PASSWORD")
                    return {"detail": "Invalid credentials"}
            else:
                print("ADMIN NOT FOUND")
                return {"detail": "Admin not found"}

    except Exception as e:
        print(f"An error occurred while fetching admin: {e}")
        return {"detail": "Server error"}

        

def create_administrator(engine, username, password):
    try:
        with Session(engine) as session:
            # Check if an admin with the same username already exists
            existing_admin = session.exec(select(Admin).where(Admin.username == username)).one_or_none()
            if existing_admin:
                return {"status": "failed", "message": f"Admin with username '{username}' already exists"}
            
            # Create a new admin user
            hashed_password = get_password_hash(password)
            admin = Admin(username=username, password_hash=hashed_password)
            session.add(admin)
            session.commit()
            
            return {"status": "success", "message": f"Admin '{username}' created successfully"}
    except Exception as e:
        print(f"An error occurred while creating admin: {e}")
        return {"status": "failed", "message": "Server error"}



def clear_table(engine, table_model):
    with engine.begin() as conn:
        conn.execute(table_model.__table__.delete())
`
## /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests

[database_setup.py](/Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests/database_setup.py)
### /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests/database_setup.py
`
import os
import sys
import json
import time
import sqlalchemy.exc

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TESTING"] = "1"  # Set the TESTING environment variable

from config import get_database_url
from sqlmodel import create_engine, select
from models import Admin
from database import create_database, create_league, add_teams_from_json, print_database, clear_table, League, create_administrator

def setup_test_db(verbose=False):
    DB_URL = get_database_url()
    TEST_DB_FILE = DB_URL.split("///")[1]
    if verbose:
        print(f"Test Database File: {TEST_DB_FILE}")
    
    engine = create_engine(DB_URL)
    
    retries = 5
    retry_delay = 1

    for attempt in range(retries):
        try:
            # Create the database if it doesn't exist
            if not os.path.exists(TEST_DB_FILE):
                create_database(engine)
            
            with engine.connect() as conn:
                league_name = "Test League"
                league_create_result = create_league(engine, league_name)

                if league_create_result["status"] == "success":
                    league_link = league_create_result["link"]
                    if verbose:
                        print(f"League '{league_name}' created with signup link: {league_link}")

                    teams_json_path = os.path.join(os.path.dirname(__file__), "test_teams.json")
                    try:
                        add_teams_from_json(engine, league_link, teams_json_path)
                        if verbose:
                            print(f"Teams added successfully from 'test_teams.json'")
                    except FileNotFoundError as e:
                        print(f"Error: 'test_teams.json' not found: {e}")
                    except json.JSONDecodeError as e:
                        print(f"Error: Invalid JSON in 'test_teams.json': {e}")
                    except sqlalchemy.exc.IntegrityError as e:
                        print(f"Error: Duplicate team name or other DB issue: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")
                else:
                    print(f"Error creating league '{league_name}': {league_create_result.get('message', 'Unknown error')}")
                    if "exception" in league_create_result:
                        raise league_create_result["exception"]

                # Create Admin User using create_administrator function
                admin_username = "Administrator"
                admin_password = "BOSSMAN"
                admin_create_result = create_administrator(engine, admin_username, admin_password)

                if admin_create_result["status"] == "success":
                    if verbose:
                        print(f"\nAdmin user '{admin_username}' created successfully.")
                else:
                    print(f"Error creating admin user: {admin_create_result.get('message', 'Unknown error')}")

                # Verify that the admin user is created
                admin_query = conn.execute(select(Admin)).all()
                if verbose:
                    print(f"Admin users in the database: {admin_query}")
                assert len(admin_query) == 1, "Admin user was not created successfully"

            break  # Break the loop if the operation is successful
        except sqlalchemy.exc.OperationalError as e:
            if attempt < retries - 1:
                print(f"Database locked. Retrying in {retry_delay} second(s)...")
                time.sleep(retry_delay)
            else:
                raise e
        finally:
        # Close the database connection
            engine.dispose()

    return engine
`
## /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests

[test_admin_login.py](/Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests/test_admin_login.py)
### /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests/test_admin_login.py
`
import os
import sys
import pytest
import time
from fastapi.testclient import TestClient
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from tests.database_setup import setup_test_db
os.environ["TESTING"] = "1"

@pytest.fixture(scope="module")
def db_engine():
    engine = setup_test_db(verbose=True)
    yield engine
    #remove test.db file from the root directory if called by this test using ../test.db otherwise it will remove the file from the root directory
    if os.path.exists("../test.db"):
        os.remove("../test.db")
    else:
        os.remove("test.db")
        time.sleep(1)

@pytest.fixture(scope="module")
def client(db_engine):
    def get_engine_override():
        return db_engine

    app.dependency_overrides[get_db_engine] = get_engine_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_team_login(client: TestClient):
    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"})
    assert response.status_code == 200
    assert "access_token" in response.json()

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid team credentials"}

def test_admin_login_missing_fields(client: TestClient):
    login_response = client.post("/admin_login", json={"username": "Administrator"})
    assert login_response.status_code == 422

    login_response = client.post("/admin_login", json={"password": "BOSSMAN"})
    assert login_response.status_code == 422
`
## /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests

[test_league.py](/Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests/test_league.py)
### /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests/test_league.py
`
import os
import sys
import pytest
import time
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from models import League
from tests.database_setup import setup_test_db
os.environ["TESTING"] = "1"

ADMIN_VALID_TOKEN = ""

@pytest.fixture(scope="module")
def db_engine():
    engine = setup_test_db(verbose=True)
    yield engine
    #remove test.db file from the root directory if called by this test using ../test.db otherwise it will remove the file from the root directory
    if os.path.exists("../test.db"):
        os.remove("../test.db")
    else:
        os.remove("test.db")
        time.sleep(1)  # Wait for the file to be removed before continuing


@pytest.fixture(scope="module")
def client(db_engine):
    def get_engine_override():
        return db_engine

    app.dependency_overrides[get_db_engine] = get_engine_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_get_token(client: TestClient):
    global ADMIN_VALID_TOKEN

    login_response = client.post("/admin_login", json={"username": "Administrator", "password": "BOSSMAN"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    ADMIN_VALID_TOKEN = token


def test_league_creation(client: TestClient):

    response = client.post("/league_create", json={"name": "week1"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]

    response = client.post("/league_create")
    assert response.status_code == 422
    
    response = client.post("/league_create", json={"name": ""})
    assert response.status_code == 200
    assert response.json() == {"status": "failed", "message": "Name is Empty"}

    response = client.post("/league_create", json={"name": "week2"}, headers={"Authorization": f"Bearer {ADMIN_VALID_TOKEN}"})
    assert response.status_code == 200
    assert "success" in response.json()["status"]

def test_league_join(client: TestClient):

    response = client.post("/league_join/MQ%3D%3D", json={"name": "std", "password": "pass", "school": "abc"})
    assert response.status_code == 200
    assert "access_token" in response.json()

`
## /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests

[test_team.py](/Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests/test_team.py)
### /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests/test_team.py
`
import os
import sys
import pytest
import time
from fastapi.testclient import TestClient
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api import app
from database import get_db_engine
from tests.database_setup import setup_test_db
os.environ["TESTING"] = "1"

@pytest.fixture(scope="module")
def db_engine():
    engine = setup_test_db(verbose=True)
    yield engine
    #remove test.db file from the root directory if called by this test using ../test.db otherwise it will remove the file from the root directory
    if os.path.exists("../test.db"):
        os.remove("../test.db")
    else:
        os.remove("test.db")
        time.sleep(1)


@pytest.fixture(scope="module")
def client(db_engine):
    def get_engine_override():
        return db_engine

    app.dependency_overrides[get_db_engine] = get_engine_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_team_login(client: TestClient):
    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "ighEMkOP"})
    assert response.status_code == 200
    assert "access_token" in response.json()

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid team credentials"}

    response = client.post("/team_login", json={"team": "BrunswickSC1", "password": "wrongpass"})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": "BrunswickSC1", "password": ""})
    assert response.status_code == 422

    response = client.post("/team_login", json={"name": " ", "password": "ighEMkOP"})
    assert response.status_code == 422
`
## /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games

[models.py](/Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/models.py)
### /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/models.py
`
from pydantic import BaseModel, field_validator
from typing import List, Optional
from sqlmodel import Field, Session, SQLModel, create_engine, Relationship
from config import CURRENT_DB
from datetime import datetime
from auth import get_password_hash, verify_password

class AdminBase(SQLModel):
    username: str = Field(unique=True, index=True)
    password_hash: str

class Admin(AdminBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        return verify_password(password, self.password_hash)

class LeagueBase(SQLModel):
    name: str = Field(unique=True, index=True)
    created_date: datetime
    expiry_date: datetime
    deleted_date: datetime | None = None
    active: bool
    signup_link: str | None = None

class League(LeagueBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    teams: List['Team'] = Relationship(back_populates='league')

class LeagueSignUp(SQLModel):
    name: str

class TeamBase(SQLModel):
    name: str = Field(index=True)
    school_name: str
    password_hash: str  # Change this field name to password_hash
    score: int = 0
    color: str = "rgb(171,239,177)"

class Team(TeamBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    league_id: int = Field(default=None, foreign_key="league.id")
    league: League = Relationship(back_populates='teams')
    submissions: List['Submission'] = Relationship(back_populates='team')

    def set_password(self, password: str):
        self.password_hash = get_password_hash(password)

    def verify_password(self, password: str):
        return verify_password(password, self.password_hash)

class SubmissionBase(SQLModel):
    code: str = Field(unique=True)
    timestamp: datetime 
    
class Submission(SubmissionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    team_id: int = Field(default=None, foreign_key='team.id')
    team: Team = Relationship(back_populates='submissions')
    

class TeamLogin(SQLModel):
    name: str
    password: str

    @field_validator('*')  # The '*' applies the validator to all fields
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v

class TeamSignUp(SQLModel):
    name: str
    password: str
    school: str

    @field_validator('*')  # The '*' applies the validator to all fields
    def check_not_empty(cls, v):
        if isinstance(v, str) and not v.strip():
            raise ValueError(f"{v} must not be empty or just whitespace.")
        return v
    
class CodeSubmit(SubmissionBase):
    pass

class AdminLogin(SQLModel):
    username: str
    password: str
`
## /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games

[config.py](/Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/config.py)
### /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/config.py
`
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
CURRENT_DIR = os.path.dirname(__file__)
CURRENT_DB = os.path.join(CURRENT_DIR, "teams.db")
GUEST_LEAGUE_EXPIRY = 24 #hours
ADMIN_LEAGUE_EXPIRY = 180 #1 week and 12 hours

def get_database_url():
    if os.environ.get("TESTING"):
        test_db_path = os.path.join(CURRENT_DIR, "test.db")  # Use a relative path for the test database
        return f"sqlite:///{test_db_path}"
        #Try an in memory db
        #return "sqlite:///:memory:"
    else:
        return f"sqlite:///{CURRENT_DB}"
`
## /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests

[test_teams.json](/Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests/test_teams.json)
### /Users/sanjindedic/Library/CloudStorage/GoogleDrive-ozrobotix@gmail.com/My Drive/PROJECTS/agent_games/tests/test_teams.json
`
{
  "teams": [
    {
      "name": "AcademyofMaryImmaculate",
      "password": "igMD3X3B",
      "school": "AcademyofMaryImmaculate"
    },
    {
      "name": "BrunswickSC1",
      "password": "ighEMkOP",
      "school": "BrunswickSC"
    },
    {
      "name": "BrunswickSC2",
      "password": "LXr0KsjO",
      "school": "BrunswickSC"
    }
  ]
}
`
