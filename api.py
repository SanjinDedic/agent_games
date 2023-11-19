from fastapi import FastAPI,UploadFile, Request, HTTPException, status, File, Query, Depends,Body
from fastapi.middleware.cors import CORSMiddleware
import inspect
import importlib.util
from multiple_players_game_nathan import run_simulation_many_times
from pydantic import BaseModel
import re
import json
import os
import asyncio

app = FastAPI()

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


def my_rank(game_state, name):
    # Extract the points_aggregate dictionary
    points_aggregate = dict()
    for player in game_state['banked_money']:
        points_aggregate[player] = game_state['banked_money'][player]+game_state['unbanked_money'][player]
    # Sort the dictionary by its values in descending order

    sorted_players = sorted(points_aggregate, key=points_aggregate.get, reverse=True)
    try:
        rank = sorted_players.index(name) + 1
        return rank
    except ValueError:
        return 0


@app.get("/")
async def root():
    return {"message": "Success, server is running"}


@app.post("/submit_agent/")
async def submit_agent(data: Source_Data):
    try:
        # Wait for 2 seconds for the processing_logic to complete
        result = await asyncio.wait_for(run_game(data: Source_Data), timeout=2)
        return result
    except asyncio.TimeoutError:
        # Logic didn't complete in 2 seconds
        return {"error": "Your agent might be stuck in an infnite loop. It took more than 2 second to sim 10 games"}


async def run_game(data: Source_Data):
    class_source = data.code
    #if the code contains the word print return an error
    if 'print' in class_source:
        return {"game_result":"Print statements are not allowed"}
    if 'exec' in class_source:
        return {"game_result":"Exec statements are not allowed"}
    if 'eval(' in class_source:
        return {"game_result":"Eval statements are not allowed"}
    if 'open(' in class_source:
        return {"game_result":"Open statements are not allowed"}
    if 'import' in class_source:
        if class_source.count('import')>1:
            return {"game_result":"Import statements are not allowed except for import random"}
        if 'import random' not in class_source:
            return {"game_result":"Import statements are not allowed except for import random"}

    with open('teams.json', 'r') as file:
        list_data = json.load(file)
        teams_list = list_data['teams']
    
    team_found = [team["name"] == data.team_name and team["password"] == data.password for team in teams_list]
    if any(team_found):
        filename = f"{data.team_name}.py"
    else:
        return {"game_result": "Team not found"}
    match = re.search(r'class (\w+)', class_source)
    if not match:
        return {"game_result":"No class definition found in the provided source code."}
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
        result = run_simulation_many_times(10, verbose=False, folder_name="test_classes")
        ranking = my_rank(result, data.team_name)

        os.remove('test_classes/'+filename)
        filepath = "classes/"+filename
        with open(filepath, 'w') as file:
            file.write("from player_base import Player\n\n")
            file.write(modified_class_source)

    except Exception as e:
        result = f"Error: {e}"

    return {"my ranking":ranking, "game_result": result}


if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)