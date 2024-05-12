import os
import logging
import json
from datetime import datetime,timedelta
from config import CURRENT_DB,CURRENT_DIR,SECRET_KEY,ADMIN_PASSWORD,ACCESS_TOKEN_EXPIRE_MINUTES
from sqlmodel import Field, SQLModel, create_engine, Session, select
from models import *
from auth import get_password_hash,verify_password,create_access_token

engine = create_engine(f'sqlite:///{CURRENT_DB}')


def get_db_session():
    with Session(engine) as session:
        yield session

def create_database():
    db_file_path = os.path.join(CURRENT_DIR, f"{CURRENT_DB}")

    # Delete the database file if it already exists
    if os.path.exists(db_file_path):
        os.remove(db_file_path)
    try:
        SQLModel.metadata.create_all(engine)
        
    except Exception as e:
        logging.error("An error occurred when creating the database", exc_info=True)
        raise e
    


def create_league(league_name, expiry_date=None):
    with Session(engine) as session:
        try:
            league = League(name=league_name, expiry_date=expiry_date)
            session.add(league)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e

def create_team(league_name,user):
    with Session(engine) as session:
        try:
            league = session.exec(select(League).where(League.name == league_name)).one()
            if league:
                hashed_pwd=get_password_hash(user.password)
                team = Team(name=user.name,school_name=user.school_name, password=hashed_pwd, league=league)
                session.add(team)
                session.commit()
                return {"status": "success", "message": "Agent Successfully created"}
            else:
                return {"status": "failed", "message": f"League '{league_name}' does not exist"}
        except Exception as e:
            session.rollback()
            raise e

def update_submission(league_name, team_name, code):
    with Session(engine) as session:
        try:
            league = session.exec(select(League).where(League.name == league_name)).one()
            team = session.exec(select(Team).where(Team.name == team_name, Team.league == league)).one()
            if team:
                submission = Submission(code=code, timestamp=datetime.now(), team=team, league=league)
                session.add(submission)
                session.commit()
            else:
                raise ValueError(f"Team '{team_name}' does not exist in league '{league_name}'")
        except Exception as e:
            session.rollback()
            raise e



def add_teams_from_json(league,teams_json_path):
    try:
        with open(teams_json_path, 'r') as file:
            data = json.load(file)
            teams_list = data['teams']

        for team in teams_list:
            create_team(league,team["name"], team["password"])

    except Exception as e:
        logging.error("An error occurred when creating the database", exc_info=True)
        raise e

def get_team(team_name,team_password):
    with Session(engine) as session:
        try:
            result = session.exec(select(Team).where(Team.name == team_name)).one()
            if verify_password(team_password, result.password):
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": team_name, "role": "student"}, 
                    expires_delta=access_token_expires
                )
                return {"access_token": access_token, "token_type": "bearer"}

            else:
                return False
        except Exception as e:
            session.rollback()
            raise e



