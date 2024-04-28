from fastapi import FastAPI,UploadFile, Request, HTTPException, status, File, Query, Depends,Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
import inspect
import logging
import importlib.util
from game_simulation import GameSimulation
from pydantic import BaseModel
import sqlite3
from datetime import datetime, timedelta
from check_file import is_safe

import traceback
import re
import json
import os
import asyncio

CURRENT_DIR = os.path.dirname(__file__)
CURRENT_DB = os.path.join(CURRENT_DIR, "teams.db")
SECRET_KEY = "AGENTBOSS"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class Team(BaseModel):
    team_name: str
    password: str

class Answer(BaseModel):
    code: str

class Admin_Simulation(BaseModel):
    password: str
    simulations: int
    score: int

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now() + expires_delta if expires_delta else datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        team_name: str = payload.get("sub")
        if team_name is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return team_name

def update_or_insert_timestamp(team_name):
    # Connect to the SQLite database
    conn = sqlite3.connect("teams_log.db")
    cursor = conn.cursor()

    # Get the current time
    current_time = datetime.now()

    try:
        # Try to retrieve the timestamp for the given team name
        cursor.execute("SELECT timestamp FROM teams_submission WHERE name = ?", (team_name,))
        result = cursor.fetchone()

        # If the team name is found in the database
        if result:
            # Parse the timestamp from the database
            last_timestamp = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')

            # Calculate the time difference
            time_difference = current_time - last_timestamp

            # If the difference is more than 1 minute, update the timestamp
            if time_difference > timedelta(minutes=1):
                cursor.execute("UPDATE teams_submission SET timestamp = ? WHERE name = ?", (current_time.strftime('%Y-%m-%d %H:%M:%S'), team_name))
                conn.commit()
                return True
            else:
                return False
        else:
            # If the team name is not found, insert a new record
            cursor.execute("INSERT INTO teams_submission (name, timestamp) VALUES (?, ?)", (team_name, current_time.strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            return True

        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()


@app.get("/")
async def root():
    return {"message": "Success, server is running"}


@app.post("/agent_login")
async def team_login(user: Team):
    try:
        result = execute_db_query("SELECT password FROM teams WHERE name=?",(user.team_name,))
        if result and result[0][0]==user.password:
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.team_name}, 
                expires_delta=access_token_expires
            )
            return {"access_token": access_token, "token_type": "bearer"}
        else:
            return {"status": "failed", "message": "No team found with these credentials"}
            
    except Exception as e:
         return {"status": "failed", "message": "Server error"}

@app.post("/submit_agent")
async def submit_agent(data: Answer, team_name: str = Depends(get_current_user)):
    try:
        #outcome = update_or_insert_timestamp(team_name)
        #if outcome:
            # Wait for 2 seconds for the processing_logic to complete
        #    result = await asyncio.wait_for(run_game(data), timeout=3)
            #if the players points are 0
        #    if "game_result" in result:
        #        if result["game_result"][team_name] == 0:
        #            return {"WARNING:":"Validated Agent is weak Score = 0"}
        #    return result
        #else:
        #    return {"error": "Your agent has been sent multiple times in one minute"}
        return {"status" : "success", "message" : "It went through"}
    except asyncio.TimeoutError:
        # Logic didn't complete in 2 seconds
        return {"error": "Your agent might be stuck in an infinite loop. It took more than 3 seconds to sim 10 games"}


async def run_game(data: Answer):
    class_source = data.code
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


def create_database():
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

        teams_json_path = os.path.join(CURRENT_DIR, 'teams.json')

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

if __name__=="__main__":
    create_database()
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)