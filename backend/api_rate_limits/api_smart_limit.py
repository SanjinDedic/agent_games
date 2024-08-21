from fastapi import FastAPI,UploadFile, Request, HTTPException, status, File, Query, Depends,Body
from fastapi.middleware.cors import CORSMiddleware
import inspect
import importlib.util
from game_simulation import GameSimulation
from pydantic import BaseModel
import sqlite3
from datetime import datetime, timedelta


import traceback
import re
import json
import os
import asyncio

app = FastAPI()

# Rate Limiting Middleware
class RateLimiter:
    def __init__(self, max_requests: int, time_window: timedelta):
        self.max_requests = max_requests
        self.time_window = time_window
        self.access_records: Dict[str, list] = {}

    def is_allowed(self, client_ip: str) -> bool:
        current_time = datetime.now()
        if client_ip not in self.access_records:
            self.access_records[client_ip] = [current_time]
            return True

        self.access_records[client_ip] = [
            t for t in self.access_records[client_ip]
            if t > current_time - self.time_window
        ]

        if len(self.access_records[client_ip]) < self.max_requests:
            self.access_records[client_ip].append(current_time)
            return True

        return False

rate_limiter = RateLimiter(max_requests=10, time_window=timedelta(minutes=1))

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Source_Data(BaseModel):
    team_name: str
    password: str
    code: str

class Admin_Simulation(BaseModel):
    password: str
    simulations: int
    score: int


def my_rank(points_aggregate, name):
    sorted_players = sorted(points_aggregate, key=points_aggregate.get, reverse=True)
    try:
        rank = sorted_players.index(name) + 1
        return rank
    except ValueError:
        return 0

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


@app.post("/submit_agent")
async def submit_agent(data: Source_Data):
    try:
        outcome = update_or_insert_timestamp(data.team_name)
        if outcome:
            # Wait for 2 seconds for the processing_logic to complete
            result = await asyncio.wait_for(run_game(data), timeout=3)
            #if the players points are 0
            if "game_result" in result:
                if result["game_result"][data.team_name] == 0:
                    return {"WARNING:":"Validated Agent is weak Score = 0"}
            return result
        else:
            return {"error": "Your agent has been sent multiple times in one minute"}
    except asyncio.TimeoutError:
        # Logic didn't complete in 2 seconds
        return {"error": "Your agent might be stuck in an infinite loop. It took more than 3 seconds to sim 10 games"}


async def run_game(data: Source_Data):
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


if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)