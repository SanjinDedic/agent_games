import json
import os
from datetime import datetime, timedelta

import pytz
from auth import create_access_token, encode_id, get_password_hash
from config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    GUEST_LEAGUE_EXPIRY,
    ROOT_DIR,
    get_database_url,
)
from models_db import (
    Admin,
    League,
    SimulationResult,
    SimulationResultItem,
    Submission,
    Team,
)
from sqlalchemy import create_engine
from sqlmodel import SQLModel, delete, select

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


class LeagueNotFoundError(Exception):
    pass


class TeamAlreadyExistsError(Exception):
    pass


class TeamNotFoundError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class SubmissionLimitExceededError(Exception):
    pass


class SimulationResultNotFoundError(Exception):
    pass


class SimulationResultTransformationError(Exception):
    pass


def get_db_engine():
    return create_engine(get_database_url())


def create_database(engine):
    SQLModel.metadata.create_all(engine)


def create_league(session, league_name, league_game, league_folder):
    league = League(
        name=league_name,
        created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
        expiry_date=(
            datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(hours=GUEST_LEAGUE_EXPIRY)
        ),
        deleted_date=(datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=7)),
        active=True,
        signup_link=None,
        folder=league_folder,
        game=league_game,
    )
    session.add(league)
    session.flush()  # Flush to generate the league ID

    league.signup_link = encode_id(league.id)
    session.commit()

    # Create the league folder
    absolute_folder = os.path.join(ROOT_DIR, "games", league.game, league.folder)
    print(f"Creating folder: {absolute_folder}")
    os.makedirs(absolute_folder, exist_ok=True)

    # Create the test_league folder
    test_league_folder = os.path.join(
        ROOT_DIR, "games", league.game, "leagues", "test_league"
    )
    os.makedirs(test_league_folder, exist_ok=True)

    # Create README.md files
    with open(os.path.join(absolute_folder, "README.md"), "w") as file:
        file.write(
            f"# {league.name}\n\nThis folder contains files for the {league.name} league."
        )

    with open(os.path.join(test_league_folder, "README.md"), "w") as file:
        file.write(
            f"# Test League for {league.game}\n\nContains test files for the {league.game} game."
        )

    return {"link": league.signup_link}


def create_team(session, name, password, league_id=1, school=None):
    league = session.exec(select(League).where(League.id == league_id)).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League with id '{league_id}' does not exist")

    existing_team = session.exec(select(Team).where(Team.name == name)).one_or_none()
    if existing_team:
        raise TeamAlreadyExistsError("Team already exists")

    team = Team(name=name, school_name=school)
    team.set_password(password)
    session.add(team)
    team.league = league
    session.commit()

    return {
        "name": team.name,
        "id": team.id,
        "league_id": team.league_id,
        "league": team.league.name,
    }


def get_team_token(session, team_name, team_password):
    team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
    if not team:
        raise TeamNotFoundError(f"Team '{team_name}' not found")

    if not team.verify_password(team_password):
        raise InvalidCredentialsError("Invalid team password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": team_name, "role": "student"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


def get_admin_token(session, username, password):
    admin = session.exec(select(Admin).where(Admin.username == username)).one_or_none()

    if admin and admin.verify_password(password):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": "admin", "role": "admin"}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        return {"detail": "Invalid credentials"}


def get_team(session, team_name):
    team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
    if not team:
        raise TeamNotFoundError(f"Team '{team_name}' not found")
    return team


def create_administrator(session, username, password):
    if len(username) == 0 or len(password) == 0:
        return {"status": "failed", "message": "Username and password are required"}
    try:
        # Check if an admin with the same username already exists
        existing_admin = session.exec(
            select(Admin).where(Admin.username == username)
        ).one_or_none()
        if existing_admin:
            return {
                "status": "failed",
                "message": f"Admin with username '{username}' already exists",
            }

        # Create a new admin user
        hashed_password = get_password_hash(password)
        admin = Admin(username=username, password_hash=hashed_password)
        session.add(admin)
        session.commit()

        return {
            "status": "success",
            "message": f"Admin '{username}' created successfully",
        }
    except Exception as e:
        print(f"An error occurred while creating admin: {e}")
        return {"status": "failed", "message": "Server error"}


def allow_submission(session, team_id):
    one_minute_ago = datetime.now(AUSTRALIA_SYDNEY_TZ) - timedelta(minutes=1)
    recent_submissions = session.exec(
        select(Submission)
        .where(Submission.team_id == team_id)
        .where(Submission.timestamp >= one_minute_ago)
    ).all()

    if len(recent_submissions) > 5:
        raise SubmissionLimitExceededError(
            "You can only make 5 submissions per minute."
        )
    return True


def save_submission(session, submission_code, team_id):
    db_submission = Submission(
        code=submission_code,
        timestamp=datetime.now(AUSTRALIA_SYDNEY_TZ),
        team_id=team_id,
    )
    session.add(db_submission)
    session.commit()  # Commit the changes to the database
    return db_submission.id


def assign_team_to_league(session, team_name, league_name):
    league = session.exec(
        select(League).where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")

    team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
    if not team:
        raise TeamNotFoundError(f"Team '{team_name}' not found")

    team.league_id = league.id
    session.add(team)
    session.commit()
    session.refresh(team)
    return f"Team '{team.name}' assigned to league '{league.name}'"


def get_league(session, league_name):
    league = session.exec(
        select(League).where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")
    return league


def get_all_admin_leagues(session):
    leagues = session.exec(select(League)).all()
    # must return a dictionary:
    return {"admin_leagues": [league.model_dump() for league in leagues]}


def delete_team(session, team_name):
    team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
    if not team:
        raise TeamNotFoundError(f"Team '{team_name}' not found")

    # Delete associated submissions
    session.exec(delete(Submission).where(Submission.team_id == team.id))

    # Delete team's code file
    if team.league_id:
        league = session.get(League, team.league_id)
        if league:
            for game_name in [
                "greedy_pig",
                "prisoners_dilemma",
            ]:  # needs to be dynamic. Config should have games list
                team_file_path = os.path.join(
                    ROOT_DIR, "games", game_name, league.folder, f"{team_name}.py"
                )
                if os.path.exists(team_file_path):
                    os.remove(team_file_path)

    # Delete team from database
    session.delete(team)
    session.commit()

    msg = f"Team '{team_name}' and its associated files deleted successfully"
    return msg


def get_all_teams(session):
    teams = session.exec(select(Team)).all()
    curated_teams = {
        "all_teams": [
            {
                "name": team.name,
                "id": team.id,
                "league_id": team.league_id,
                "league": team.league.name,
            }
            for team in teams
        ]
    }
    return curated_teams


def save_simulation_results(session, league_id, results, rewards=None):
    timestamp = datetime.now(AUSTRALIA_SYDNEY_TZ)

    rewards_str = (
        json.dumps(rewards) if rewards is not None else "[10, 8, 6, 4, 3, 2, 1]"
    )

    simulation_result = SimulationResult(
        league_id=league_id,
        timestamp=timestamp,
        num_simulations=results["num_simulations"],
        custom_rewards=rewards_str,
    )
    session.add(simulation_result)
    session.flush()

    custom_value_names = list(results.get("table", {}).keys())[
        :3
    ]  # Get up to 3 custom value names

    for team_name, score in results["total_points"].items():
        team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
        if team:
            result_item = SimulationResultItem(
                simulation_result_id=simulation_result.id, team_id=team.id, score=score
            )
            print(f"Saving simulation results for team '{team_name}'")
            for i, name in enumerate(custom_value_names, start=1):
                value = results["table"][name]
                if isinstance(value, dict):
                    setattr(result_item, f"custom_value{i}", value.get(team_name))
                else:
                    setattr(result_item, f"custom_value{i}", value)
                setattr(result_item, f"custom_value{i}_name", name)

            session.add(result_item)

    session.commit()
    print(f"Simulation results saved successfully for league ID {league_id}")
    return simulation_result


def get_published_result(session, league_name):
    league = session.exec(
        select(League).where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")
    active = False
    expiry_date = league.expiry_date
    if expiry_date.tzinfo is None:
        expiry_date = AUSTRALIA_SYDNEY_TZ.localize(expiry_date)
    if expiry_date > datetime.now(AUSTRALIA_SYDNEY_TZ):
        active = True

    for sim in league.simulation_results:
        if sim.published:
            total_points = {}
            table = {}
            num_simulations = sim.num_simulations
            for result in sim.simulation_results:
                total_points[result.team.name] = result.score
                for i in range(1, 4):
                    value_name = getattr(result, f"custom_value{i}_name")
                    value = getattr(result, f"custom_value{i}")
                    if value_name:
                        if value_name not in table:
                            table[value_name] = {}
                        table[value_name][result.team.name] = value

            if sim.feedback_str is not None:
                feedback = sim.feedback_str
            elif sim.feedback_json is not None:
                feedback = json.loads(sim.feedback_json)
            else:
                feedback = None

            return {
                "league_name": league_name,
                "id": sim.id,
                "total_points": total_points,
                "table": table,
                "num_simulations": num_simulations,
                "active": active,
                "rewards": json.loads(sim.custom_rewards),
                "feedback": feedback,
            }

    return None


def process_simulation_results(sim, league_name, active=None):
    total_points = {}
    table_data = {}

    for result in sim.simulation_results:
        team_name = result.team.name

        # Handle total points
        total_points[team_name] = result.score

        # Handle custom values
        for i in range(1, 4):
            custom_value = getattr(result, f"custom_value{i}")
            custom_value_name = getattr(result, f"custom_value{i}_name")

            if custom_value_name:
                if custom_value_name not in table_data:
                    table_data[custom_value_name] = {}

                table_data[custom_value_name][team_name] = custom_value

    # Add feedback handling
    if sim.feedback_str is not None:
        feedback = sim.feedback_str
    elif sim.feedback_json is not None:
        feedback = json.loads(sim.feedback_json)
    else:
        feedback = None

    result_data = {
        "league_name": league_name,
        "id": sim.id,
        "total_points": total_points,
        "table": table_data,
        "num_simulations": sim.num_simulations,
        "timestamp": sim.timestamp,
        "rewards": sim.custom_rewards,
        "feedback": feedback,  # Add feedback to response
    }

    if active is not None:
        result_data["active"] = active

    return result_data


class SimulationResultFormatError(Exception):
    pass


def get_all_league_results(session, league_name):
    league = session.exec(
        select(League).where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")

    all_results = [
        process_simulation_results(sim, league_name)
        for sim in league.simulation_results
    ]

    # Sort all results by id in reverse with the highest first
    all_results = sorted(all_results, key=lambda x: x["id"], reverse=True)

    return {"all_results": all_results}


def publish_sim_results(session, league_name, sim_id, feedback=None):
    league = session.exec(
        select(League).where(League.name == league_name)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(f"League '{league_name}' not found")

    simulation = session.exec(
        select(SimulationResult).where(SimulationResult.id == sim_id)
    ).one_or_none()
    if not simulation:
        raise SimulationResultNotFoundError(
            f"Simulation result with ID '{sim_id}' not found"
        )

    # Set all published results to false for this league
    for sim in league.simulation_results:
        sim.published = False
        session.add(sim)

    simulation.published = True

    # Handle feedback if provided
    if feedback is not None:
        if isinstance(feedback, str):
            simulation.feedback_str = feedback
            simulation.feedback_json = None
        elif isinstance(feedback, dict):
            simulation.feedback_str = None
            simulation.feedback_json = json.dumps(feedback)

    session.add(simulation)
    session.commit()

    return f"Simulation results for league '{league_name}' published successfully", {
        "id": simulation.id,
        "league_name": league_name,
        "published": True,
    }


def get_all_published_results(session):
    current_time = datetime.now(AUSTRALIA_SYDNEY_TZ)
    all_results = []

    for league in session.exec(select(League)).all():
        expiry_date = league.expiry_date
        if expiry_date.tzinfo is None:
            expiry_date = AUSTRALIA_SYDNEY_TZ.localize(expiry_date)
        active = expiry_date >= current_time

        for sim in league.simulation_results:
            if sim.published:
                all_results.append(process_simulation_results(sim, league.name, active))

    return {"all_results": all_results}


def update_expiry_date(session, league_name, expiry_date):
    print("EXPIRY DATE: ", expiry_date, "LEAGUE NAME: ", league_name)
    league = session.exec(
        select(League).where(League.name == league_name)
    ).one_or_none()
    if league:
        print("LEAGUE FOUND", league)
        league.expiry_date = expiry_date
        session.add(league)
        session.commit()
        return f"Expiry date for league '{league_name}' updated successfully"
    else:
        print("LEAGUE NOT FOUND", league_name)
        return f"League '{league_name}' not found"
