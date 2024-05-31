# test_json_teams.py

import os
import sys
import pytest
import json
from sqlmodel import Session, select
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import Team

from database import get_db_engine, create_team
from utils import add_teams_from_json
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

def test_add_teams_from_json(db_session, tmpdir, mocker):
    teams_json_path = tmpdir.join("teams.json")
    teams_json_path.write('''
    {
      "teams": [
        {
          "name": "TestTeam1",
          "password": "password1",
          "school": "TestSchool1"
        },
        {
          "name": "TestTeam2",
          "password": "password2",
          "school": "TestSchool2"
        }
      ]
    }
    ''')

    mock_create_team = mocker.patch("utils.create_team", return_value={"status": "success"})

    add_teams_from_json(db_session, str(teams_json_path))

    assert mock_create_team.call_count == 2
    mock_create_team.assert_any_call(session=db_session, name="TestTeam1", password="password1", school="TestSchool1")
    mock_create_team.assert_any_call(session=db_session, name="TestTeam2", password="password2", school="TestSchool2")

def test_add_teams_from_json_missing_fields(db_session, tmpdir):
    teams_json_path = tmpdir.join("teams_missing_fields.json")
    teams_json_path.write('''
    {
      "teams": [
        {
          "name": "TestTeam1"
        }
      ]
    }
    ''')

    with pytest.raises(ValueError) as excinfo:
        add_teams_from_json(db_session, str(teams_json_path))
    assert "Invalid team data in JSON: missing required fields" in str(excinfo.value)

def test_add_teams_from_json_file_not_found(db_session):
    teams_json_path = "nonexistent_file.json"

    with pytest.raises(FileNotFoundError) as excinfo:
        add_teams_from_json(db_session, teams_json_path)
    assert f"Error: 'teams_json_path' not found at: {teams_json_path}" in str(excinfo.value)

def test_add_teams_from_json_invalid_json(db_session, tmpdir):
    teams_json_path = tmpdir.join("teams_invalid_json.json")
    teams_json_path.write('''
    {
      "teams": [
        {
          "name": "TestTeam1",
          "password": "password1",
          "school": "TestSchool1"
        },
        {
          "name": "TestTeam2",
          "password": "password2",
          "school": "TestSchool2"
        }
      ]
    ''')  # Missing closing bracket to make the JSON invalid

    with pytest.raises(ValueError) as excinfo:
        add_teams_from_json(db_session, str(teams_json_path))
    assert "Error: Invalid JSON format in" in str(excinfo.value)

def test_add_teams_from_json_create_team_failed(db_session, tmpdir, mocker):
    teams_json_path = tmpdir.join("teams.json")
    teams_json_path.write('''
    {
      "teams": [
        {
          "name": "TestTeam1",
          "password": "password1",
          "school": "TestSchool1"
        }
      ]
    }
    ''')

    mock_create_team = mocker.patch("utils.create_team", return_value={"status": "failed", "message": "Failed to create team"})

    with pytest.raises(ValueError) as excinfo:
        add_teams_from_json(db_session, str(teams_json_path))
    assert "Failed to create team 'TestTeam1': Failed to create team" in str(excinfo.value)