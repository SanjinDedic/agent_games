from fastapi import FastAPI, HTTPException, status, File, Query, Depends, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import create_engine
from check_file import is_safe
import asyncio
from config import get_database_url, ACCESS_TOKEN_EXPIRE_MINUTES
from contextlib import asynccontextmanager
from models import *
from auth import get_current_user, create_access_token
from datetime import timedelta
from database import (
    create_database, 
    create_league,
    get_team, 
    get_admin,
    create_team,
    print_database
)

engine = create_engine(get_database_url())

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_database(engine)
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
async def league_create(league: LeagueSignUp, authorization: str = Header(None)):
    try:
        if not league.name:
            return {"status": "failed", "message": "Name is Empty"}
        elif authorization and authorization.startswith("Bearer "):
            if get_current_user(authorization.split(" ")[1])["role"] == "admin":
                return create_league(engine=engine, league_name=league.name)
        else:
            return create_league(engine=engine, league_name=league.name)
    except Exception as e:
        return {"status": "failed", "message": "Server error"}

@app.post("/league_join/{link}")
async def league_join(link, user: TeamSignUp):
    print("link" + link)
    try:
        user_data = TeamSignUp.model_validate(user)
        print(user_data)
        return create_team(engine=engine, league_link=link, name=user.name, password=user.password, school=user.school)
    except Exception as e:
        return {"status": "failed", "message": "Server error"}
    

@app.post("/team_login")
def team_login(credentials: TeamLogin):
    team = get_team(engine, credentials.name, credentials.password)
    if team:
        return team
    else:
        raise HTTPException(status_code=401, detail="Invalid team credentials")

@app.post("/team_create")
async def agent_create(user: TeamBase):
    try:
        return create_team(engine=engine, link=user.link, name=user.name, password=user.password, school=user.school_name)
    except Exception as e:
        return {"status": "failed", "message": "Server error"}

@app.post("/submit_agent")
async def submit_agent(data: CodeSubmit, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        if is_safe(data.code):
            # output = execute_code_in_docker(data.code)
            # update_submission(team_name,code)
            return {"status": "success", "message": "It went through"}
        else:
            return {"error": "Code is unsafe to execute"}
    except asyncio.TimeoutError:
        # Logic didn't complete in 2 seconds
        return {"error": "Your agent might be stuck in an infinite loop. It took more than 3 seconds to sim 10 games"}

@app.post("/admin_login")
def admin_login(login: AdminLogin):
    print("calling get_admin with" + login.username + " " + login.password)
    print("database" + str(engine))
    print_database(engine)
    result = get_admin(engine, login.username, login.password)
    if "detail" in result:
        raise HTTPException(status_code=401, detail=result["detail"])
    return result

@app.post("/run_simulation")
async def run_simulation(number_of_runs: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"status": "success", "message": "result"}