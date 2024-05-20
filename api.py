from fastapi import FastAPI, HTTPException, status, File, Query, Depends, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import create_engine, select
from check_file import is_safe
import asyncio
import os
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
from greedy_pig_sim import run_simulations

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
                #create a folder for the league in /leagues/admin/league_name and a README.md file that says "This is the league_name league"
                os.makedirs(f"leagues/admin/{league.name}", exist_ok=True)
                with open(f"leagues/admin/{league.name}/README.md", "w") as f:
                    f.write(f"This is the {league.name} league")
                return create_league(engine=engine, league_name=league.name)
            else:
                raise HTTPException(status_code=403, detail="Forbidden")
        else:
            os.makedirs(f"leagues/user/{league.name}", exist_ok=True)
            with open(f"leagues/user/{league.name}/README.md", "w") as f:
                f.write(f"This is the {league.name} league")
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
async def submit_agent(submission: SubmissionCode, current_user: dict = Depends(get_current_user)):
    print("submit_agent called")
    team_name = current_user["team_name"]
    user_role = current_user["role"]
    print("submit_agent called and parsed")
    try:
        # Get the team's league from the database
        with Session(engine) as session:
            team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")
            league = team.league
        print("team and league found")
        #validation
        #step 1 add player to test_league
        league_folder = "leagues/test_league"
        file_path = os.path.join(league_folder, f"{team_name}.py")
        with open(file_path, "w") as file:
            file.write(submission.code)
        print("file written")
        #step 2 run 100 simulations
        results = run_simulations(100)
        print("simulations run")
        # Create the league folder if it doesn't exist
        league_folder = os.path.join(f"leagues/{'admin' if user_role == 'student' else 'user'}/{league.name}")
        print(team_name, user_role, league.name)
        print(league_folder)
        os.makedirs(league_folder, exist_ok=True)

        # Save the submitted code in a Python file named after the team
        file_path = os.path.join(league_folder, f"{team_name}.py")
        with open(file_path, "w") as file:
            file.write(submission.code)
        print("are we here")
        # Log the submission in the database
        with Session(engine) as session:
            db_submission = Submission(code=submission.code, timestamp=datetime.now(), team_id=team.id)
            session.add(db_submission)
            session.commit()
            submission_id = db_submission.id

        return {"message": f"Code submitted successfully. Submission ID: {submission_id}", "results": results}

    except Exception as e:
        print(f"Error updating submission: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating submission")


@app.post("/admin_login")
def admin_login(login: AdminLogin):
    print("calling get_admin with" + login.username + " " + login.password)
    print("database" + str(engine))
    print_database(engine)
    result = get_admin(engine, login.username, login.password)
    if "detail" in result:
        raise HTTPException(status_code=401, detail=result["detail"])
    return result



# Run simulation will be called from the front end to run the simulation
# The simulation is specific to a League so the league name is passed as a parameter
# The simulation will run for a specified number of runs which are also a parameter
# The simulation will be run only if the user is an admin
# The simulation will return the results of the simulation
@app.post("/run_simulation")
async def run_simulation(number_of_runs: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"status": "success", "message": "result"}