import os
from sqlmodel import Session, SQLModel, create_engine
from models import League, Team, Admin
from auth import get_password_hash
from config import CURRENT_DB, ADMIN_LEAGUE_EXPIRY
from datetime import datetime, timedelta

def set_up_test_db():
    os.environ["TESTING"] = "1"  # Set the TESTING environment variable to "0"
    
    engine = create_engine(f"sqlite:///{CURRENT_DB}")
    print(f"Database URL: {CURRENT_DB}")
    SQLModel.metadata.create_all(engine)
    print("Database with engine created successfully.")


    with Session(engine) as session:
        # Create an admin league called unnassigned
        admin_leagues = []
        unnassigned = League(
            name="unassigned",
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
            active=True,
            folder="leagues/admin/unassigned",
            game="greedy_pig"
        )
        admin_leagues.append(unnassigned)

        
        for i in range(1, 4):
            league_name = f"week{i}"
            league = League(
                name=league_name,
                created_date=datetime.now(),
                expiry_date=(datetime.now() + timedelta(hours=ADMIN_LEAGUE_EXPIRY)),
                active=True,
                folder=f"leagues/admin/{league_name}",
                game="greedy_pig"
            )
            admin_leagues.append(league)
        session.add_all(admin_leagues)



        # Create 12 teams with their passwords
        teams = [
            {"name": "team1", "password": "pass1"},
            {"name": "team2", "password": "pass2"},
            {"name": "team3", "password": "pass3"},
            {"name": "team4", "password": "pass4"},
            {"name": "team5", "password": "pass5"},
            {"name": "team6", "password": "pass6"},
            {"name": "team7", "password": "pass7"},
            {"name": "team8", "password": "pass8"},
            {"name": "team9", "password": "pass9"},
            {"name": "team10", "password": "pass10"},
            {"name": "team11", "password": "pass11"},
            {"name": "team12", "password": "pass12"}
        ]

        for team_data in teams:
            team = Team(
                name=team_data["name"],
                school_name=f"School {team_data['name']}",
                password_hash=get_password_hash(team_data["password"]),
                league_id=1
            )
            session.add(team)

        session.commit()

        print("Database populated successfully.")

if __name__ == "__main__":
    set_up_test_db()

"""
TO DO:
1. create a test db file
2. create a test db engine
3. use with Session(engine) as session:
4. create an admin league called unassigned
5. create an admin league called comp_test
6. Create an Administrator if it doesn't exist 
7. Creaate teams from test_teams.json

"""


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
from database import create_database, create_league, add_teams_from_json, print_database, League, create_administrator

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
                league_name = "comp_test"
                league_create_result = create_league(engine, league_name, league_game="greedy_pig", league_folder="leagues/admin/comp_test")

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



