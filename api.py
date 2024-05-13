from fastapi import FastAPI, HTTPException, status, File, Query, Depends,Body
from fastapi.middleware.cors import CORSMiddleware
from check_file import is_safe
import asyncio

from contextlib import asynccontextmanager
from models import *
from auth import get_current_user
from database import *
from game import Game


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_database()
    yield


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Success, server is up and running (deploy.yml works1)"}


@app.post("/league_create")
async def league_create(user: LeagueSignUp):
    try:
        if not user.name:
            return {"status": "failed", "message": "Name is Empty"}
        else:
            return create_league(user.name)
         
    except Exception as e:
         print(e)
         return {"status": "failed", "message": "Server error"}

@app.post("/league_join/{link}")
async def league_join(link ,user: TeamSignUp):
    try:
        return create_team(link,user.name,user.password,user.school)
         
    except Exception as e:
         return {"status": "failed", "message": "Server error"}

@app.post("/agent_login")
async def team_login(user: TeamLogin):
    try:
        team = get_team(user.name,user.password)
        if team is not False:
            return team
        else:
            return {"status": "failed", "message": "No team found with these credentials"}
            
    except Exception as e:
         return {"status": "failed", "message": "Server error"}

@app.post("/agent_create")
async def agent_create(user: TeamBase):
    try:
        return create_team(user)
         
    except Exception as e:
         return {"status": "failed", "message": "Server error"}


@app.post("/submit_agent")
async def submit_agent(data: CodeSubmit, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        if is_safe(data.code):
            
            #output = execute_code_in_docker(data.code)
            #update_submission(team_name,code)
            return {"status" : "success", "message" : "It went through"}
        else:
            return {"error": "Code is unsafe to execute"}
        
        
    except asyncio.TimeoutError:
        # Logic didn't complete in 2 seconds
        return {"error": "Your agent might be stuck in an infinite loop. It took more than 3 seconds to sim 10 games"}
    

@app.post("/admin_login")
async def admin_login(a: AdminLogin):
    if not a.password:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    return get_admin(a.password)
    
    
    

@app.post("/run_simulation")
async def run_simulation(number_of_runs: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {"status": "success", "message": "result"}
