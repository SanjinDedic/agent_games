from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    DemoUser,
    League,
    SimulationResult,
    SimulationResultItem,
    Submission,
    Team,
)


def test_get_demo_users(client, auth_headers, setup_demo_data):
    response = client.get("admin/get_all_demo_users", headers=auth_headers)
    data = response.json()
    print("HERE ARE ALL THDEMO USERS:", data)
    assert response.status_code == 200
    assert "demo_users" in data["data"]
    assert "demo_team_name" in data["data"]["demo_users"][0]


def test_delete_all_demo_users(client, auth_headers, setup_demo_data, db_session):
    response = client.post("/admin/delete_demo_teams_and_subs", headers=auth_headers)
    data = response.json()
    print("DATA  ", data)
    assert response.status_code == 200
    # make sure that there are no demo_ teams in the database

    response = client.get("/admin/get_all_demo_users", headers=auth_headers)
    demo_users = response.json()
    assert demo_users["data"] == {"demo_users": []}

    # check that there are no
    # Direct database verification for teams
    demo_teams = db_session.exec(select(Team).where(Team.is_demo == True)).all()
    assert len(demo_teams) == 0
    orphaned_submissions = db_session.exec(
        # ~ means not and when combined with .in_ its like saying WHERE SUB NOT IN . .
        select(Submission).where(~Submission.team_id.in_(select(Team.id)))
    ).all()
    assert len(orphaned_submissions) == 0

    # check there are no results / result items that are orphaned
    orphaned_result_items = db_session.exec(
        select(SimulationResultItem).where(
            ~SimulationResultItem.team_id.in_(select(Team.id))
        )
    ).all()

    assert len(orphaned_result_items) == 0
