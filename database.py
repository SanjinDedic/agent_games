import sqlite3
import os
import logging
from fastapi import FastAPI, HTTPException
import json
from passlib.context import CryptContext
from datetime import datetime
from config import CURRENT_DB,CURRENT_DIR

def execute_db_query(query, params=(), fetchone=False, db=None):
    if db is None:
        db=CURRENT_DB
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        if fetchone:
            return c.fetchone()
        else:
            return c.fetchall()
    except Exception as e:
        logging.error("Error occurred when executing database query", exc_info=True)
        raise e
    finally:
        conn.close()




def create_database(data, teams_json_path):
    db_file_path = os.path.join(CURRENT_DIR, f"{CURRENT_DB}")

    # Delete the database file if it already exists
    if os.path.exists(db_file_path):
        os.remove(db_file_path)
    try:
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()
        
        # Define tables
        teams_table = """
        CREATE TABLE "teams" (
            "name"	TEXT NOT NULL UNIQUE,
            "password"	TEXT NOT NULL,
            "score"	TEXT NOT NULL,
            PRIMARY KEY("name")
        );
        """

        submission_table = """
        CREATE TABLE "submissions" (
            "name"	TEXT NOT NULL UNIQUE,
            "code"	TEXT NOT NULL,
            "timestamp" TEXT NOT NULL,
            FOREIGN KEY("name") REFERENCES "teams"("name")
        );"""

        cursor.execute(teams_table)
        cursor.execute(submission_table)

        with open(teams_json_path, 'r') as file:
            data = json.load(file)
            teams_list = data['teams']

        for team in teams_list:
            cursor.execute("INSERT INTO teams (name, password, score) VALUES (?,?,?)",(team["name"], team["password"], 0))

        conn.commit()
        conn.close()
    except Exception as e:
        logging.error("An error occurred when creating the database", exc_info=True)
        raise e
    
async def run_game(data):
    class_source = data
    #if the code contains the word print return an error
    if 'print' in class_source:
        return {"invalid":"Print statements are not allowed"}
    if 'exec' in class_source:
        return {"invalid":"Exec statements are not allowed"}
    if 'eval(' in class_source:
        return {"invalid":"Eval statements are not allowed"}
    if 'open(' in class_source:
        return {"invalid":"Open statements are not allowed"}
    if 'import' in class_source:
        if class_source.count('import')>1:
            return {"invalid":"Import statements are not allowed except for import random"}
        if 'import random' not in class_source:
            return {"invalid":"Import statements are not allowed except for import random"}

    with open('teams.json', 'r') as file:
        list_data = json.load(file)
        teams_list = list_data['teams']
    
    team_found = [team["name"] == data.team_name and team["password"] == data.password for team in teams_list]
    if any(team_found):
        filename = f"{data.team_name}.py"
    else:
        return {"Error": "Team not found"}
    match = re.search(r'class (\w+)', class_source)
    if not match:
        return {"Error":"No class definition found in the provided source code."}
    class_name = match.group(1)
    filepath = "test_classes/"+filename
    modified_class_definition = f"class {class_name}(Player):"
    modified_class_source = re.sub(r'class \w+\(\):', modified_class_definition, class_source)

    # Write the source code to a temporary file
    with open(filepath, 'w') as file:
        file.write("from player import Player\n\n")
        file.write(modified_class_source)

    # Dynamically import the class
    spec = importlib.util.spec_from_file_location(class_name, filepath)
    player_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(player_module)

    try:
        simulation = GameSimulation()
        simulation.set_folder("test_classes")
        result = simulation.run_simulation_many_times(50, verbose=False)
        ranking = my_rank(result, data.team_name)
        os.remove('test_classes/'+filename)
        filepath = "classes/"+filename
        with open(filepath, 'w') as file:
            file.write("from player import Player\n\n")
            file.write(modified_class_source)

    except Exception as e:
        # Print the error message and the traceback
        error_message = f"Error: {e}"
        print(error_message)
        traceback.print_exc()

        # and return it along with the error message
        error_traceback = traceback.format_exc()
        result = {"Error": error_message, "Traceback": error_traceback}
        return result

    return {"my ranking":str(ranking) +"/10","games played": 50, "game_result": result}

