import sqlite3
import os
import logging
from fastapi import FastAPI, HTTPException
import json
from datetime import datetime,timedelta
from config import CURRENT_DB,CURRENT_DIR,SECRET_KEY,ADMIN_PASSWORD



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


def update_submission(team_name,code):
    
    try:
        # Get the current time
        current_time = datetime.now()
        result = execute_db_query("SELECT timestamp FROM submission WHERE name = ?", (team_name,),fetchone=True)
        
        # If the team name is found in the database
        if result:
            execute_db_query("UPDATE teams_submission SET timestamp = ?, code = ? WHERE name = ?", (current_time.strftime('%Y-%m-%d %H:%M:%S'),code, team_name,))
        else:
            # If the team name is not found, insert a new record
            execute_db_query("INSERT INTO submission (name, code, timestamp) VALUES (?, ?, ?)", (team_name, code, current_time.strftime('%Y-%m-%d %H:%M:%S'),))

    except Exception as e:
        print(f"An error occurred: {e}")
    



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
    
async def run_game(code):
    
    try:
        simulation = GameSimulation()
        simulation.set_folder("test_classes")
        result = simulation.run_simulation_many_times(50, verbose=False)
        ranking = my_rank(result, data.team_name)
        os.remove('test_classes/'+filename)
        filepath = "classes/"+filename
        
    except Exception as e:
       
        result = {"Error": e}
        return result

    return {"my ranking":str(ranking) +"/10","games played": 50, "game_result": result}

