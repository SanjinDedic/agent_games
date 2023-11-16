from fastapi import FastAPI,UploadFile, Request, HTTPException, status, File, Query, Depends,Body
from fastapi.middleware.cors import CORSMiddleware
import inspect
import importlib.util
from single_player_game import run_single_simulation
from pydantic import BaseModel
import re
import json
import os

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


@app.get("/")
async def root():
    return {"message": "Success, server is running"}


@app.post("/submit_agent/")
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
        if 'import random' not in class_source:
            return {"game_result":"Import statements are not allowed except for import random"}
        if 'import random' in class_source:
            #make sure that import random is the only import statement
            if class_source.count('import')>1:
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
    filepath = "classes/"+filename
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
    PlayerClass = getattr(player_module, class_name)

    # Run a single simulation (if this takes more than 5 second return an error)
    result = run_single_simulation(PlayerClass,data.team_name,data.password)
    if result=='Not Validated' or result=='Not Validated: Stuck in endless loop':
        os.remove('classes/'+filename)

    return {"game_result": result}


if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)