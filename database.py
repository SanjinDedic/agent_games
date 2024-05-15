import os
import logging
import json
from datetime import datetime,timedelta
from config import CURRENT_DB,CURRENT_DIR,GUEST_LEAGUE_EXPIRY,ADMIN_PASSWORD,ADMIN_LEAGUE_EXPIRY
from sqlmodel import Field, SQLModel, create_engine, Session, select
from models import *
from auth import *

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
    


def create_league(league_name):
    with Session(engine) as session:
        try:
            league = League(name=league_name,created_date=datetime.now(), expiry_date=(datetime.now()+timedelta(hours=GUEST_LEAGUE_EXPIRY)),deleted_date=(datetime.now()+timedelta(days=7)), active=True,signup_link=None)
            session.add(league)
            session.commit()
            session.refresh(league)
            

            league.signup_link = encode_id(league.id)
            session.add(league)
            session.commit()

            return {"status" : "success", "link": league.signup_link}
        except Exception as e:
            session.rollback()
            return {"status" : "failed"}
    
    

def create_admin_league(league_name):
    with Session(engine) as session:
        try:
            league = League(name=league_name,created_date=datetime.now(), expiry_date=(datetime.now()+timedelta(hours=ADMIN_LEAGUE_EXPIRY)),deleted_date=None, active=True,signup_link=None)
            session.add(league)
            session.commit()
            session.refresh(league)
            

            league.signup_link = encode_id(league.id)
            session.add(league)
            session.commit()
            session.refresh(league)

            teams_json_path = os.path.join(CURRENT_DIR, "teams.json")
            add_teams_from_json(league.signup_link,teams_json_path)

            return {"status" : "success", "link": league.signup_link}
        except Exception as e:
            session.rollback()
            raise e

def create_team(league_link,name,password,school=None):
    with Session(engine) as session:
        try:
            league = session.exec(select(League).where(League.signup_link == league_link)).one_or_none()
            if league:
                hashed_pwd=get_password_hash(password)
                team = Team(name=name,school_name=school, password=hashed_pwd, league=league)
                session.add(team)
                session.commit()

                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": name, "role": "student"}, 
                    expires_delta=access_token_expires
                )
                return {"access_token": access_token, "token_type": "bearer"}
            else:
                return {"status": "failed", "message": f"League '{league_link}' does not exist"}
        except Exception as e:
            session.rollback()
            print(e)
            raise e

def update_submission(league_name, team_name, code):
    with Session(engine) as session:
        try:
            league = session.exec(select(League).where(League.name == league_name)).one_or_none()
            team = session.exec(select(Team).where(Team.name == team_name, Team.league == league)).one_or_none()
            if league and team:
                submission = Submission(code=code, timestamp=datetime.now(), team=team, league=league)
                session.add(submission)
                session.commit()
            else:
                raise ValueError(f"Team '{team_name}' does not exist in league '{league_name}'")
        except Exception as e:
            session.rollback()
            raise e



def add_teams_from_json(league_link,teams_json_path):
    try:
        with open(teams_json_path, 'r') as file:
            data = json.load(file)
            teams_list = data['teams']

        for team in teams_list:
            create_team(league_link,team["name"], team["password"],team["school"])

    except Exception as e:
        raise e

def get_team(team_name,team_password):
    with Session(engine) as session:
        try:
            result = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
            if result and verify_password(team_password, result.password):
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

def get_admin(password):
    if password != ADMIN_PASSWORD:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    else:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": "admin", "role": "admin"}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

