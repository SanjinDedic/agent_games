import logging
import json
import os
import pytz
from datetime import datetime, timedelta
from sqlalchemy.exc import OperationalError
from sqlmodel import select, SQLModel, delete
from config import ACCESS_TOKEN_EXPIRE_MINUTES, get_database_url, GUEST_LEAGUE_EXPIRY, ROOT_DIR
from models_db import Admin, League, Team, Submission, SimulationResult, SimulationResultItem
from sqlalchemy import create_engine
from sqlmodel import Session, select
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    encode_id
)
class LeagueNotFoundError(Exception):
    pass

class TeamNotFoundError(Exception):
    pass

class InvalidCredentialsError(Exception):
    pass

class SubmissionLimitExceededError(Exception):
    pass

class SimulationResultNotFoundError(Exception):
    pass

def get_db_engine():
    return create_engine(get_database_url())

def create_database(engine, prnt=False):
    SQLModel.metadata.create_all(engine)

def create_league(session, league_name, league_game, league_folder):
    aest_timezone = pytz.timezone('Australia/Sydney')
    
    league = League(
        name=league_name,
        created_date=datetime.now(aest_timezone),
        expiry_date=(datetime.now(aest_timezone) + timedelta(hours=GUEST_LEAGUE_EXPIRY)),
        deleted_date=(datetime.now(aest_timezone) + timedelta(days=7)),
        active=True,
        signup_link=None,
        folder=league_folder,
        game=league_game
    )
    session.add(league)
    session.flush()  # Flush to generate the league ID
    
    league.signup_link = encode_id(league.id)
    session.commit()

    absolute_folder = os.path.join(ROOT_DIR, "games", league.game, league_folder.lstrip("/"))
    os.makedirs(absolute_folder, exist_ok=True)

    with open(os.path.join(absolute_folder, "README.md"), "w") as file:
        file.write(f"# {league_name}\n\nThis folder contains files for the {league_name} league.")

    return {"link": league.signup_link}


def create_team(session, name, password, league_id=1, school=None):
    league = session.exec(
        select(League)
        .where(League.id == league_id)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League with id '{league_id}' does not exist")
    
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


def get_team_token(session, team_name, team_password):
    team = session.exec(
        select(Team)
        .where(Team.name == team_name)
    ).one_or_none()
    if not team:
        raise TeamNotFoundError(f"Team '{team_name}' not found")
    
    if not team.verify_password(team_password):
        raise InvalidCredentialsError("Invalid team password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": team_name, "role": "student"}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

def get_admin_token(session, username, password):
    admin = session.exec(
        select(Admin)
        .where(Admin.username == username)
    ).one_or_none()

    if admin and admin.verify_password(password):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": "admin", "role": "admin"},
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        return {"detail": "Invalid credentials"}

def get_team(session, team_name):
    team = session.exec(
        select(Team)
        .where(Team.name == team_name)
    ).one_or_none()
    if not team:
        raise TeamNotFoundError(f"Team '{team_name}' not found")
    return team


def create_administrator(session, username, password):
    if len(username) == 0 or len(password) == 0:
        return {"status": "failed", "message": "Username and password are required"}
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
    
def allow_submission(session, team_id):
    one_minute_ago = datetime.now(pytz.timezone('Australia/Sydney')) - timedelta(minutes=1)
    recent_submissions = session.exec(
        select(Submission)
        .where(Submission.team_id == team_id)
        .where(Submission.timestamp >= one_minute_ago)
    ).all()

    if len(recent_submissions) > 2:
        raise SubmissionLimitExceededError("You can only make 3 submissions per minute.")
    return True

def save_submission(session, submission_code, team_id):
    aest_timezone = pytz.timezone('Australia/Sydney')
    db_submission = Submission(code=submission_code, timestamp=datetime.now(aest_timezone), team_id=team_id)
    session.add(db_submission)
    session.commit()  # Commit the changes to the database
    return db_submission.id

def assign_team_to_league_in_db(session, team_name, league_name):
    league = session.exec(
        select(League)
        .where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")
    
    team = session.exec(
        select(Team)
        .where(Team.name == team_name)).one_or_none()
    if not team:
        raise TeamNotFoundError(f"Team '{team_name}' not found")
    
    team.league_id = league.id
    session.add(team)
    session.commit()
    session.refresh(team)
    return  f"Team '{team.name}' assigned to league '{league.name}'"

def get_league(session, league_name):
    league = session.exec(
        select(League)
        .where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")
    return league
    
def get_all_admin_leagues_from_db(session):
    leagues = session.exec(select(League)).all()
    #must return a dictionary:
    return { "admin_leagues": [league.model_dump() for league in leagues]}

def delete_team_from_db(session, team_name):
    team = session.exec(
        select(Team)
        .where(Team.name == team_name)).one_or_none()
    if not team:
        raise TeamNotFoundError(f"Team '{team_name}' not found")
    
    # Delete associated submissions
    session.exec(delete(Submission).where(Submission.team_id == team.id))
    
    session.delete(team)
    session.commit()
    msg = f"Team '{team_name}' deleted successfully"
    return msg
    

def get_all_teams_from_db(session):
    teams = session.exec(select(Team)).all()
    curated_teams = {"all_teams": [{"name": team.name, "id": team.id, "league_id": team.league_id, "league": team.league.name} for team in teams]}
    return curated_teams

def save_simulation_results(session, league_id, results):
    aest_timezone = pytz.timezone("Australia/Sydney")
    timestamp = datetime.now(aest_timezone)
    simulation_result = SimulationResult(league_id=league_id, timestamp=timestamp, num_simulations=results["num_simulations"])
    session.add(simulation_result)
    print("SAVED SIMULATION RESULT: ", simulation_result)
    session.flush()  # Flush to generate the simulation_result_id
    
    for team_name, score in results["total_points"].items():
        print("TEAM NAME: ", team_name, "SCORE: ", score)
        team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
        if team:
            wins = results["total_wins"][team.name]
            result_item = SimulationResultItem(simulation_result_id=simulation_result.id, team_id=team.id, score=score, wins=wins)
            session.add(result_item)

    session.commit()
    return simulation_result.id


def get_all_league_results_from_db(session, league_name):
    league = session.exec(select(League).where(League.name == league_name)).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")
    all_results = []
    for sim in league.simulation_results:
        #we need to get data from SimulationResultItem and return it in this format {"league_name": league_name, "id":sim.id, "total_points": total_points, "total_wins": total_wins, "num_simulations": num_simulations}
        total_points = {}
        total_wins = {}
        timestamp = sim.timestamp
        num_simulations = sim.num_simulations
        for result in sim.simulation_results:
            total_points[result.team.name] = result.score
            total_wins[result.team.name] = result.wins
        all_results.append({"league_name": league_name, "id":sim.id, "total_points": total_points, "total_wins": total_wins, "num_simulations": num_simulations, "timestamp": timestamp})
        #sort all results by id in reverse with the highest first
        all_results = sorted(all_results, key=lambda x: x["id"], reverse=True)
    return {"all_results": all_results}



def publish_sim_results(session, league_name, sim_id):
    league = session.exec(select(League).where(League.name == league_name)).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")
    
    simulation = session.exec(select(SimulationResult).where(SimulationResult.id == sim_id)).one_or_none()
    if not simulation:
        raise SimulationResultNotFoundError(f"Simulation result with ID '{sim_id}' not found")
    
    # Set all published results to false for this league
    for sim in league.simulation_results:
        sim.published = False
        session.add(sim)

    simulation.published = True
    session.add(simulation)
    session.commit()
    return f"Simulation results for league '{league_name}' published successfully", {"id": simulation.id, "league_name": league_name, "published": True}


def get_published_result(session, league_name):
    league = session.exec(select(League).where(League.name == league_name)).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")
    active = False
    expiry_date = league.expiry_date
    if expiry_date.tzinfo is None:
        expiry_date = pytz.timezone("Australia/Sydney").localize(expiry_date)
    if expiry_date > datetime.now(pytz.timezone("Australia/Sydney")):
        active = True
    
    for sim in league.simulation_results:
        if sim.published:
            total_points = {}
            total_wins = {}
            num_simulations = sim.num_simulations
            for result in sim.simulation_results:
                total_points[result.team.name] = result.score
                total_wins[result.team.name] = result.wins

            return {"league_name": league_name, "id": sim.id, "total_points": total_points, "total_wins": total_wins, "num_simulations": num_simulations, "active": active}
    
    return None


def get_all_published_results(session):
    current_time = datetime.now(pytz.timezone("Australia/Sydney"))
    all_results = []
    for league in session.exec(select(League)).all():
        expiry_date = league.expiry_date
        if expiry_date.tzinfo is None:
            expiry_date = pytz.timezone("Australia/Sydney").localize(expiry_date)
        active = expiry_date >= current_time
        for sim in league.simulation_results:
            if sim.published:
                total_points = {}
                total_wins = {}
                num_simulations = sim.num_simulations
                for result in sim.simulation_results:
                    total_points[result.team.name] = result.score
                    total_wins[result.team.name] = result.wins

                all_results.append({
                    "league_name": league.name, 
                    "id": sim.id, 
                    "total_points": total_points, 
                    "total_wins": total_wins, 
                    "num_simulations": num_simulations, 
                    "active": active
                })
    return {"all_results": all_results}



def update_expiry_date_in_db(session, league_name, expiry_date):
    print("EXPIRY DATE: ", expiry_date, "LEAGUE NAME: ", league_name)
    league = session.exec(
        select(League)
        .where(League.name == league_name)).one_or_none()
    if league:
        print("LEAGUE FOUND", league)
        league.expiry_date = expiry_date
        session.add(league)
        session.commit()
        return f"Expiry date for league '{league_name}' updated successfully"
    else:
        print("LEAGUE NOT FOUND", league_name)
        return f"League '{league_name}' not found"