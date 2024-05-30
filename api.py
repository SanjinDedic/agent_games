from fastapi import FastAPI, HTTPException, status, File, Query, Depends, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import create_engine, select
from validation import is_agent_safe, run_agent_simulation
from games.greedy_pig.greedy_pig_sim import run_simulations
import asyncio
import os
from config import get_database_url, ACCESS_TOKEN_EXPIRE_MINUTES, ROOT_DIR
from contextlib import asynccontextmanager
from models import *
from auth import get_current_user, create_access_token, decode_id
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

        return create_league(engine=engine, league_name=league.name, league_game=league.game, league_folder=league_folder)

    except HTTPException as e:
        raise e
    except Exception as e:
        return {"status": "failed", "message": "Server error"}

@app.post("/league_join/{link}")
async def league_join(link, user: TeamSignUp):
    #ths will only apply to user created leagues
    #find league_id from link
    try:
        league_id = decode_id(link)
        user_data = TeamSignUp.model_validate(user)
        print(user_data)
        return create_team(engine=engine, name=user.name, password=user.password, league_id=league_id, school=user.school)
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
async def agent_create(user: TeamSignup):
    try:
        return create_team(engine=engine, name=user.name, password=user.password, school=user.school_name)
    except Exception as e:
        return {"status": "failed", "message": "Server error"}


@app.post("/submit_agent")
async def submit_agent(submission: SubmissionCode, current_user: dict = Depends(get_current_user)):
    team_name = current_user["team_name"]
    user_role = current_user["role"]
    if not is_agent_safe(submission.code):
        return {"status": "error", "message": "Agent code is not safe."}
    results = run_agent_simulation(submission.code, team_name)
    if not results:
        return {"status": "error", "message": "Agent simulation failed."}
    try:
        # Get the team's league from the database
        with Session(engine) as session:
            team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
            game = team.league.game
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")
            league = team.league
        print("team and league found")
        #the league must have a game associated with it!!
        #the folder depends on the game and admin status

        # Create the league folder if it doesn't exist
        # if user is logged in use the admin folder else use the user folder
        if team.league.folder:
            league_folder = team.league.folder
        else:
            league_folder = f"leagues/user/{league.name}"
        print(team_name, user_role, league.name)

        # Save the submitted code in a Python file named after the team
        file_path = os.path.join(ROOT_DIR,"games","greedy_pig",league_folder, f"{team_name}.py")
        with open(file_path, "w") as file:
            file.write(submission.code)
        print("are we here")
        # Log the submission in the database
        with Session(engine) as session:
            print(submission.code)
            print(team.id)
            db_submission = Submission(code=submission.code, timestamp=datetime.now(), team_id=team.id)
            session.add(db_submission)
            session.commit()
            submission_id = db_submission.id
        #return {"message": f"Code submitted successfully. Submission ID: {submission_id}", "results": results}
        return {"message": f"Code submitted successfully. Submission ID: {submission_id}", "results": results, "team_name": team_name}

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


@app.post("/run_simulation", response_model=SimulationResult)
def run_simulation(simulation_config: SimulationConfig, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can run simulations")

    league_name = simulation_config.league_name
    num_simulations = simulation_config.num_simulations

    statement = select(League).where(League.name == league_name)
    with Session(engine) as session:
        league = session.exec(statement).one_or_none()

    if not league:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"League '{league_name}' not found")

    try:
        results = run_simulations(num_simulations, league)
        return SimulationResult(results=results)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
@app.get("/get_all_admin_leagues")
def get_all_admin_leagues():
    with Session(engine) as session:
        statement = select(League).where(League.folder.like("leagues/admin/%"))
        leagues = session.exec(statement).all()
        return leagues
    
if __name__ == "__main__":
    import uvicorn
    from production_database_setup import setup_test_db
    os.environ["TESTING"] = "0"
    setup_test_db(engine)
    uvicorn.run(app, host="0.0.0.0", port=8000)