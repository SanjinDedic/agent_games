from fastapi import FastAPI, HTTPException, status, File, Query, Depends, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import create_engine, select, Session
from validation import is_agent_safe, run_agent_simulation
from games.greedy_pig.greedy_pig_sim import run_simulations
import asyncio
import os
from config import get_database_url, ACCESS_TOKEN_EXPIRE_MINUTES, ROOT_DIR
from contextlib import asynccontextmanager
from models import *
from auth import get_current_user, create_access_token, decode_id
from database import (
    create_league,
    get_team_token,
    get_admin,
    create_team,
    get_team,
    get_db_engine,
    save_submission,
    assign_team_to_league,
    get_league,
    get_all_admin_leagues_from_db,
    delete_team_from_db,
    toggle_league_active_status,
    get_all_teams_from_db,
    save_simulation_results,
    get_all_league_results_from_db
)

os.environ["TESTING"] = "0"  # Set the TESTING environment variable to "0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    engine = get_db_engine()
    print(f"Database URL: {engine.url}")  # Add this line
    with Session(engine) as session:
        yield session

@app.get("/")
async def root():
    return {"message": "Success, server is up and running (deploy.yml works1)"}

@app.post("/league_create")
async def league_create(league: LeagueSignUp, authorization: str = Header(None), session: Session = Depends(get_db)):
    try:
        if not league.name:
            return {"status": "failed", "message": "Name is Empty"}

        user_role = "user"
        if authorization and authorization.startswith("Bearer "):
            user = get_current_user(authorization.split(" ")[1])
            if user["role"] == "admin":
                user_role = "admin"
        #Do we need to give a token to a visior that has not logged in and call them a visitor??
        if user_role == "admin":
            league_folder = f"/leagues/admin/{league.name}"
        else:
            league_folder = f"/leagues/user/{league.name}"

        return create_league(session=session, league_name=league.name, league_game=league.game, league_folder=league_folder)

    except HTTPException as e:
        raise e
    except Exception as e:
        return {"status": "failed", "message": "Server error"}

@app.post("/league_join/{link}") #rename to user_league_join
async def league_join(link, user: TeamSignUp, session: Session = Depends(get_db)):
    #ths will only apply to user created leagues
    #find league_id from link
    try:
        league_id = decode_id(link)
        user_data = TeamSignUp.model_validate(user)
        print(user_data)
        return create_team(session=session, name=user.name, password=user.password, league_id=league_id, school=user.school)
    except Exception as e:
        return {"status": "failed", "message": "Server error"}
    

@app.post("/team_login")
def team_login(credentials: TeamLogin, session: Session = Depends(get_db)):
    team_token = get_team_token(session, credentials.name, credentials.password)
    if team_token:
        return team_token
    else:
        raise HTTPException(status_code=401, detail="Invalid team credentials")

@app.post("/team_create")
async def agent_create(user: TeamSignup, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin users can create teams")
    try:
        return create_team(session=session, name=user.name, password=user.password, school=user.school_name)
    except Exception as e:
        return {"status": "failed", "message": "Server error {e}"}


@app.post("/submit_agent")
async def submit_agent(submission: SubmissionCode, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    team_name = current_user["team_name"]
    user_role = current_user["role"]
    if not is_agent_safe(submission.code):
        return {"status": "error", "message": "Agent code is not safe."}
    results = run_agent_simulation(submission.code, team_name)
    if not results:
        return {"status": "error", "message": "Agent simulation failed."}
    try:
        team = get_team(session, team_name)
        print("team found", team.name, team.league.name, team.league.folder)
        if team.league.folder:
            league_folder = team.league.folder
        else:
            league_folder = f"leagues/user/{team.league.name}"
        print(team_name, user_role, team.league.name)

        # Save the submitted code in a Python file named after the team
        file_path = os.path.join(ROOT_DIR,"games","greedy_pig",league_folder, f"{team_name}.py")
        with open(file_path, "w") as file:
            file.write(submission.code)
        print("are we here")
        # Log the submission in the database
        print(submission.code)
        print(team.id)
        submission_id = save_submission(session, submission.code, team.id)
        return {"message": f"Code submitted successfully. Submission ID: {submission_id}", "results": results, "team_name": team_name}

    except Exception as e:
        print(f"Error updating submission: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating submission")


@app.post("/admin_login")
def admin_login(login: AdminLogin, session: Session = Depends(get_db)):
    print("calling get_admin with" + login.username + " " + login.password)
    result = get_admin(session, login.username, login.password)
    if "detail" in result:
        raise HTTPException(status_code=401, detail=result["detail"])
    return result


@app.post("/run_simulation", response_model=SimulationResult)
def run_simulation(simulation_config: SimulationConfig, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can run simulations")

    league_name = simulation_config.league_name
    num_simulations = simulation_config.num_simulations
    try:
        results = run_simulations(num_simulations, get_league(session, league_name))
        if league_name != "test_league":
            save_simulation_results(session, league_name, results)
        return SimulationResult(results=results)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    

@app.get("/get_all_admin_leagues")
def get_all_admin_leagues(session: Session = Depends(get_db)):
    return get_all_admin_leagues_from_db(session)
    

@app.post("/league_assign")
async def submit_agent(league: LeagueAssignRequest, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    print("winner")
    team_name = current_user["team_name"]
    print("team_name", team_name, "about to assign to league", league.name)
    if current_user["role"] not in ["admin", "student"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can assign teams to leagues")
    assignment_status = assign_team_to_league(session, team_name, league.name)
    return assignment_status


@app.post("/delete_team")
async def delete_team(team: TeamDelete, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can delete teams")
    return delete_team_from_db(session, team.name)


@app.post("/toggle_league_active")
async def toggle_league_active(league: LeagueActive, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can toggle league active status")
    return toggle_league_active_status(session, league.name)


@app.get("/get_all_teams")
def get_all_teams(session: Session = Depends(get_db)):
    return get_all_teams_from_db(session)

@app.post("/get_all_league_results")
def get_all_league_results(league: LeagueActive, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can view league results")
    return get_all_league_results_from_db(session, league.name)