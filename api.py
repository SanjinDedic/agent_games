from fastapi import FastAPI,UploadFile, Request, HTTPException, status, File, Query, Depends,Body
from fastapi.middleware.cors import CORSMiddleware
import inspect
import importlib.util
from multiple_players_game_nathan import run_simulation_many_times
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


import traceback
import re
import json
import os
import asyncio

app = FastAPI()


limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter





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


@app.get("/")
async def root():
    return {"message": "Success, server is running"}


@app.post("/submit_agent")
@limiter.limit("2/minute")
async def submit_agent(request: Request, data: Source_Data):
    try:
        # Wait for 2 seconds for the processing_logic to complete
        result = await asyncio.wait_for(run_game(data), timeout=2)
        #if the players points are 0
        if "game_result" in result:
            if result["game_result"][data.team_name] == 0:
                return {"WARNING:":"Validated Agent is weak Score = 0"}
        return result
    except asyncio.TimeoutError:
        # Logic didn't complete in 2 seconds
        return {"error": "Your agent might be stuck in an infinite loop. It took more than 2 seconds to sim 10 games"}


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
        file.write("from player_base import Player\n\n")
        file.write(modified_class_source)

    # Dynamically import the class
    spec = importlib.util.spec_from_file_location(class_name, filepath)
    player_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(player_module)

    try:
        result = run_simulation_many_times(50, verbose=False, folder_name="test_classes")
        ranking = my_rank(result, data.team_name)
        os.remove('test_classes/'+filename)
        filepath = "classes/"+filename
        with open(filepath, 'w') as file:
            file.write("from player_base import Player\n\n")
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


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded"
    )


if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)