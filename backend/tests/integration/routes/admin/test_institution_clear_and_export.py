from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.tests.conftest import add_submission, build_institution
from backend.database.db_models import (
    AgentAPIKey,
    Institution,
    League,
    LeagueType,
    SimulationResult,
    SimulationResultItem,
    Submission,
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketCategory,
    SupportTicketStatus,
    SupportTicketSubmitterType,
    Team,
    TeamType,
)
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def seeded_institution(db_session: Session) -> Institution:
    """Institution with unassigned + extra league, student + agent team,
    submission, sim result, agent API key, and a support ticket + attachment."""
    now = datetime.now()

    institution = build_institution(
        name="clear_export_test_inst",
        contact_person="C",
        contact_email="c@example.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=30),
        docker_access=True,
        password_hash="hashed",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    unassigned = League(
        name="unassigned",
        created_date=now,
        expiry_date=now + timedelta(days=365),
        game="greedy_pig",
        league_type=LeagueType.INSTITUTION,
        institution_id=institution.id,
    )
    other_league = League(
        name="comp_league",
        created_date=now,
        expiry_date=now + timedelta(days=30),
        game="greedy_pig",
        league_type=LeagueType.STUDENT,
        institution_id=institution.id,
    )
    db_session.add_all([unassigned, other_league])
    db_session.commit()
    db_session.refresh(unassigned)
    db_session.refresh(other_league)

    student_team = Team(
        name="ce_student_team",
        school_name="School A",
        password_hash="h",
        league_id=other_league.id,
        team_type=TeamType.STUDENT,
        institution_id=institution.id,
    )
    agent_team = Team(
        name="ce_agent_team",
        school_name="AI Agent",
        league_id=other_league.id,
        team_type=TeamType.AGENT,
        institution_id=institution.id,
    )
    db_session.add_all([student_team, agent_team])
    db_session.commit()
    db_session.refresh(student_team)
    db_session.refresh(agent_team)

    add_submission(
        db_session,
        code="print('hello')",
        timestamp=now,
        team_id=student_team.id,
        duration_ms=10.5,
    )

    sim_result = SimulationResult(
        league_id=other_league.id,
        timestamp=now,
        num_simulations=1,
    )
    db_session.add(sim_result)
    db_session.commit()
    db_session.refresh(sim_result)

    sim_item = SimulationResultItem(
        simulation_result_id=sim_result.id,
        team_id=student_team.id,
        score=5.0,
    )
    db_session.add(sim_item)

    api_key = AgentAPIKey(key="secret-key-abcd1234", team_id=agent_team.id)
    db_session.add(api_key)

    ticket = SupportTicket(
        category=SupportTicketCategory.BUG,
        subject="Test ticket",
        description="desc",
        status=SupportTicketStatus.OPEN,
        submitter_type=SupportTicketSubmitterType.INSTITUTION,
        institution_id=institution.id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    attachment = SupportTicketAttachment(
        ticket_id=ticket.id,
        s3_key="fake-s3-key.png",
        content_type="image/png",
        size_bytes=10,
        original_filename="image.png",
    )
    db_session.add(attachment)
    db_session.commit()

    return institution


def test_clear_institution_data_success(client, auth_headers, seeded_institution, db_session):
    inst_id = seeded_institution.id

    response = client.post(
        "/admin/institution-clear-data",
        headers=auth_headers,
        json={"id": inst_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success", data
    assert data["data"]["teams_deleted"] == 2
    assert data["data"]["leagues_deleted"] == 1  # comp_league only; unassigned kept
    assert data["data"]["tickets_deleted"] == 1

    # Institution row still present
    db_session.expire_all()
    assert db_session.get(Institution, inst_id) is not None

    # Unassigned league still present, comp_league gone
    remaining_leagues = db_session.exec(
        select(League).where(League.institution_id == inst_id)
    ).all()
    assert len(remaining_leagues) == 1
    assert remaining_leagues[0].name == "unassigned"

    # Teams, submissions, sim results, sim items, api keys, tickets, attachments gone
    assert db_session.exec(
        select(Team).where(Team.institution_id == inst_id)
    ).all() == []
    assert db_session.exec(select(Submission)).all() == []
    assert db_session.exec(select(SimulationResult)).all() == []
    assert db_session.exec(select(SimulationResultItem)).all() == []
    assert db_session.exec(select(AgentAPIKey)).all() == []
    assert db_session.exec(
        select(SupportTicket).where(SupportTicket.institution_id == inst_id)
    ).all() == []
    assert db_session.exec(select(SupportTicketAttachment)).all() == []


def test_clear_institution_data_not_found(client, auth_headers):
    response = client.post(
        "/admin/institution-clear-data",
        headers=auth_headers,
        json={"id": 99999},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()


def test_clear_institution_data_unauthorized(client):
    response = client.post(
        "/admin/institution-clear-data",
        json={"id": 1},
    )
    assert response.status_code == 401


def test_clear_institution_data_wrong_role(client):
    wrong_token = create_access_token(
        data={"sub": "x", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/admin/institution-clear-data",
        headers={"Authorization": f"Bearer {wrong_token}"},
        json={"id": 1},
    )
    assert response.status_code == 403


def test_export_institution_data_success(client, auth_headers, seeded_institution):
    inst_id = seeded_institution.id

    response = client.get(
        f"/admin/institution-export/{inst_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success", body
    dump = body["data"]

    assert dump["schema_version"] == 1
    assert "exported_at" in dump

    inst = dump["institution"]
    assert inst["id"] == inst_id
    assert inst["name"] == "clear_export_test_inst"
    assert "password_hash" not in inst

    assert len(dump["leagues"]) == 2
    league_names = {lg["name"] for lg in dump["leagues"]}
    assert {"unassigned", "comp_league"} == league_names

    assert len(dump["teams"]) == 2
    for team in dump["teams"]:
        assert "password_hash" not in team

    assert len(dump["submissions"]) == 1
    assert dump["submissions"][0]["code"] == "print('hello')"

    assert len(dump["simulation_results"]) == 1
    assert len(dump["simulation_result_items"]) == 1

    assert len(dump["agent_api_keys"]) == 1
    api_key = dump["agent_api_keys"][0]
    assert "key" not in api_key  # raw key never exported
    assert api_key["key_masked"] == "***1234"

    assert len(dump["support_tickets"]) == 1
    ticket = dump["support_tickets"][0]
    assert ticket["subject"] == "Test ticket"
    assert len(ticket["attachments"]) == 1
    assert ticket["attachments"][0]["s3_key"] == "fake-s3-key.png"


def test_export_institution_not_found(client, auth_headers):
    response = client.get(
        "/admin/institution-export/99999",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert "not found" in body["message"].lower()


def test_export_institution_unauthorized(client):
    response = client.get("/admin/institution-export/1")
    assert response.status_code == 401


def test_delete_institution_with_agent_team_regression(
    client, auth_headers, seeded_institution, db_session
):
    """Regression: previously delete_institution crashed on AgentAPIKey FK
    (institution had an agent team with an API key) and on SupportTicket FK
    (institution_id was referenced). Should now succeed."""
    inst_id = seeded_institution.id

    response = client.post(
        "/admin/institution-delete",
        headers=auth_headers,
        json={"id": inst_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success", data

    db_session.expire_all()
    assert db_session.get(Institution, inst_id) is None
    assert db_session.exec(
        select(League).where(League.institution_id == inst_id)
    ).all() == []
    assert db_session.exec(select(AgentAPIKey)).all() == []
    assert db_session.exec(
        select(SupportTicket).where(SupportTicket.institution_id == inst_id)
    ).all() == []
