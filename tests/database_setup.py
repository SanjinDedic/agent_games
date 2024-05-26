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