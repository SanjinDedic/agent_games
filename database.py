import logging
import json
import os
import pytz
from datetime import datetime, timedelta, UTC
from sqlalchemy.exc import OperationalError
from sqlmodel import select, SQLModel
from config import CURRENT_DB, ACCESS_TOKEN_EXPIRE_MINUTES, get_database_url, GUEST_LEAGUE_EXPIRY, ROOT_DIR
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

def create_league(session, league_name, league_game, league_folder):
    print("CREATE LEAGUE CALLED!")
    try:
        aest_timezone = pytz.timezone('Australia/Sydney')
        
        league = League(
            name=league_name,
            created_date=datetime.now(aest_timezone),
            expiry_date=(datetime.now(aest_timezone) + timedelta(hours=GUEST_LEAGUE_EXPIRY)),
            deleted_date=(datetime.now(aest_timezone) + timedelta(days=7)),
            active=True,
            signup_link=None,
            folder=league_folder,  # this needs to start with /leagues and end with the league name (need a validator for this )
            game=league_game
        )
        session.add(league)
        session.flush()  # Flush to generate the league ID
        
        league.signup_link = encode_id(league.id)
        session.commit()
        #create the folder for the league
        absolute_folder = ROOT_DIR +"/games/" +f"{league.game}/"+league_folder
        #print("/games/" +f"{league.game}")
        print("ROOT DIR: ", ROOT_DIR)
        print("LEAGUE FOLDER: ", league_folder)
        print("MAKING FOLDER FOR LEAGUE: ", absolute_folder)
        if league_folder:
            os.makedirs(absolute_folder, exist_ok=True)
            #insert a README file with the league name
            with open(os.path.join(absolute_folder, "README.md"), "w") as file:
                file.write(f"# {league_name}\n\nThis folder contains files for the {league_name} league.")

            
            return {"status": "success", "link": league.signup_link}
    except Exception as e:
        return {"status": "failed", "message": str(e)}


def create_team(session, name, password, league_id=1, school=None):
    print("CREATE TEAM CALLED!")
    try:
        league = session.exec(select(League).where(League.id == league_id)).one_or_none()
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
            print(f"League with id '{league_id}' does not exist")
            return {"status": "failed", "message": f"League with id '{league_id}' does not exist"}
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {"status": "failed", "message": "Server error"}


def add_teams_from_json(session, league_link, teams_json_path):
    try:
        with open(teams_json_path, 'r') as file:
            data = json.load(file)
            teams_list = data.get('teams', [])  # Use .get to safely handle missing 'teams' key

        for team_data in teams_list:
            # Check if all required fields are present in team_data
            required_fields = ["name", "password"]
            if not all(field in team_data for field in required_fields):
                raise ValueError("Invalid team data in JSON: missing required fields")

            create_result = create_team(session=session, name=team_data["name"], password=team_data["password"], school=team_data.get("school", None))
            
            # Check for errors in team creation
            if create_result.get("status") == "failed":
                raise ValueError(f"Failed to create team '{team_data['name']}': {create_result['message']}")
            
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: 'teams_json_path' not found at: {teams_json_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Error: Invalid JSON format in '{teams_json_path}': {e}")
    except (ValueError, KeyError) as e:  # Catch specific errors for better messages
        raise ValueError(f"Error processing team data from JSON: {e}")

def get_team_token(session, team_name, team_password):
    try:
        result = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
        print("RESULT: ", result)
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

def get_admin(session, username, password):
    try:
        statement = select(Admin).where(Admin.username == username)
        admin = session.exec(statement).one_or_none()

        if admin and admin.verify_password(password):
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": "admin", "role": "admin"},
                expires_delta=access_token_expires
            )
            return {"access_token": access_token, "token_type": "bearer"}
        else:
            return {"detail": "Invalid credentials"}
    except Exception as e:
        print(f"An error occurred while fetching admin: {e}")
        return {"detail": "Server error"}

def get_team(session, team_name):
    try:
        team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
        if team:
            return team
        else:
            return {"status": "failed", "message": f"Team '{team_name}' not found"}
    except Exception as e:
        print(f"An error occurred while fetching team: {e}")
        return {"status": "failed", "message": "Server error"}


def create_administrator(session, username, password):
    try:
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
    
def save_submission(session, submission_code, team_id):
    aest_timezone = pytz.timezone('Australia/Sydney')
    db_submission = Submission(code=submission_code, timestamp=datetime.now(aest_timezone), team_id=team_id)
    session.add(db_submission)
    session.commit()  # Commit the changes to the database
    return db_submission.id

def assign_team_to_league(session, team_name, league_name):
    print("ASSIGN TEAM TO LEAGUE CALLED!")
    league = session.exec(select(League).where(League.name == league_name)).one_or_none()
    if not league:
        return {"message": f"League '{league_name}' not found"}
    team_name = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
    team_name.league_id = league.id
    session.add(team_name)
    session.commit()
    return {"message": f"Team '{team_name.name}' assigned to league '{league.name}'"}