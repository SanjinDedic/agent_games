To refactor your code and improve your database to achieve 3NF and store simulation results as integers in a separate table, you can make the following changes:

1. Update the `SimulationResult` model in `models.py`:

```python
class SimulationResult(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    league_id: int = Field(foreign_key="league.id")
    league: League = Relationship(back_populates="simulation_results")
    timestamp: datetime
    simulation_results: List["SimulationResultItem"] = Relationship(back_populates="simulation_result")

class SimulationResultItem(SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)
    simulation_result_id: int = Field(foreign_key="simulationresult.id")
    simulation_result: SimulationResult = Relationship(back_populates="simulation_results")
    team_id: int = Field(foreign_key="team.id")
    team: Team = Relationship()
    score: int
```

In this updated model, we introduce a new table `SimulationResultItem` to store individual simulation results as integers. Each `SimulationResultItem` is associated with a `SimulationResult` and a `Team`.

2. Update the `League` model in `models.py` to include a relationship with `SimulationResult`:

```python
class League(SQLModel, table=True):
    # ...
    simulation_results: List["SimulationResult"] = Relationship(back_populates="league")
    # ...
```

3. Update the `save_simulation_results` function in `database.py`:

```python
def save_simulation_results(session, league_id, results):
    aest_timezone = pytz.timezone("Australia/Sydney")
    timestamp = datetime.now(aest_timezone)
    simulation_result = SimulationResult(league_id=league_id, timestamp=timestamp)
    session.add(simulation_result)
    session.flush()  # Flush to generate the simulation_result_id

    for team_name, score in results.items():
        team = session.exec(select(Team).where(Team.name == team_name)).one_or_none()
        if team:
            result_item = SimulationResultItem(simulation_result_id=simulation_result.id, team_id=team.id, score=score)
            session.add(result_item)

    session.commit()
```

In this updated function, we create a new `SimulationResult` instance and save it to the database. Then, for each team and score in the `results` dictionary, we create a `SimulationResultItem` instance and associate it with the `SimulationResult` and the corresponding `Team`.

4. Update the `get_all_league_results_from_db` function in `database.py`:

```python
def get_all_league_results_from_db(session, league_id):
    statement = select(SimulationResult).where(SimulationResult.league_id == league_id).order_by(SimulationResult.timestamp.desc())
    results = session.exec(statement).all()
    return results
```

In this updated function, we retrieve the `SimulationResult` instances based on the `league_id` instead of the `league_name`.

5. Update the `run_simulation` endpoint in `api.py`:

```python
@app.post("/run_simulation", response_model=SimulationResult)
def run_simulation(simulation_config: SimulationConfig, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    # ...
    try:
        results = run_simulations(num_simulations, get_league(session, league_name))
        if league_name != "test_league":
            league = get_league(session, league_name)
            save_simulation_results(session, league.id, results)
        return SimulationResult(results=results)
    # ...
```

In this updated endpoint, we pass the `league.id` instead of the `league_name` to the `save_simulation_results` function.

With these changes, your database will be in 3NF, and simulation results will be stored as integers in a separate table (`SimulationResultItem`) associated with the `SimulationResult` and `Team` tables.

Remember to update any other parts of your code that rely on the previous structure of the `SimulationResult` model and the `save_simulation_results` and `get_all_league_results_from_db` functions.