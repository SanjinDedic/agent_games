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
    assert demo_users["data"] == None

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


def test_get_demo_users_exceptions(client, auth_headers, db_session, mocker):
    # Test case 1: Database error during team query
    mocker.patch(
        "backend.routes.admin.admin_db.session.exec",
        side_effect=Exception("Database connection error"),
    )

    response = client.get("/admin/get_all_demo_users", headers=auth_headers)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "error"
    assert "database" in data["message"].lower()

    # Test case 2: Error during result processing
    # First restore normal session.exec
    mocker.patch.stopall()

    # Then make a specific method fail
    original_append = list.append

    def mocked_append(self, item):
        if "demo_team_name" in item:
            raise Exception("Processing error")
        return original_append(self, item)

    mocker.patch("builtins.list.append", mocked_append)

    response = client.get("/admin/get_all_demo_users", headers=auth_headers)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "error"
    assert "processing" in data["message"].lower()

    # Test case 3: Server error with no details
    mocker.patch.stopall()
    mocker.patch(
        "backend.routes.admin.admin_db.get_all_demo_users", side_effect=Exception()
    )

    response = client.get("/admin/get_all_demo_users", headers=auth_headers)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "error"
    assert "unexpected error" in data["message"].lower()


def test_delete_all_demo_users_exceptions(
    client, auth_headers, setup_demo_data, db_session, mocker
):
    # Test case 1: Database error during team query
    mocker.patch(
        "backend.routes.admin.admin_db.session.exec",
        side_effect=Exception("Database connection error"),
    )

    response = client.post("/admin/delete_demo_teams_and_subs", headers=auth_headers)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "error"
    assert "database" in data["message"].lower()

    # Test case 2: Error during deletion process
    mocker.patch.stopall()

    # Patch database session delete to fail
    def mock_delete_fail(obj):
        if isinstance(obj, Team) and obj.is_demo:
            raise Exception("Unable to delete demo team")

    mocker.patch("backend.routes.admin.admin_db.session.delete", mock_delete_fail)

    response = client.post("/admin/delete_demo_teams_and_subs", headers=auth_headers)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "error"
    assert "unable to delete" in data["message"].lower()

    # Test case 3: Rollback failure
    mocker.patch.stopall()

    # Make transaction rollback fail
    def mock_rollback_fail():
        raise Exception("Transaction rollback failed")

    mocker.patch("backend.routes.admin.admin_db.session.rollback", mock_rollback_fail)
    mocker.patch(
        "backend.routes.admin.admin_db.session.delete",
        side_effect=Exception("Deletion error that triggers rollback"),
    )

    response = client.post("/admin/delete_demo_teams_and_subs", headers=auth_headers)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "error"
    # The message depends on how your code handles nested exceptions
    assert "error" in data["message"].lower()

    # Test case 4: Commit failure
    mocker.patch.stopall()

    def mock_commit_fail():
        raise Exception("Failed to commit transaction")

    mocker.patch("backend.routes.admin.admin_db.session.commit", mock_commit_fail)

    response = client.post("/admin/delete_demo_teams_and_subs", headers=auth_headers)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "error"
    assert "commit" in data["message"].lower()
