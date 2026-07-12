"""League-tutorial attachments: selection at league creation, the
get/update-league-tutorials endpoints, ownership, and FK cleanup on delete."""

import pytest
from sqlmodel import Session, select

from backend.database.db_models import League, LeagueTutorial, Tutorial


@pytest.fixture
def tutorials(db_session: Session) -> list:
    """Two tutorials in the global library."""
    created = []
    for title in ["Python Basics", "Greedy Pig Prep"]:
        tutorial = Tutorial(title=title, description=f"{title} description")
        db_session.add(tutorial)
        created.append(tutorial)
    db_session.commit()
    for tutorial in created:
        db_session.refresh(tutorial)
    return created


def get_league_links(db_session: Session, league_id: int) -> list:
    return list(
        db_session.exec(
            select(LeagueTutorial.tutorial_id)
            .where(LeagueTutorial.league_id == league_id)
            .order_by(LeagueTutorial.tutorial_id)
        ).all()
    )


def test_league_create_with_tutorials(
    client, institution_headers, db_session, tutorials
):
    tutorial_ids = [t.id for t in tutorials]
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "league_with_tutorials",
            "game": "greedy_pig",
            "tutorial_ids": tutorial_ids,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert sorted(data["tutorial_ids"]) == sorted(tutorial_ids)
    assert get_league_links(db_session, data["league_id"]) == sorted(tutorial_ids)

    # The endpoint reads them back
    response = client.post(
        "/institution/get-league-tutorials",
        headers=institution_headers,
        json={"league_id": data["league_id"]},
    )
    assert response.status_code == 200
    assert response.json()["tutorial_ids"] == sorted(tutorial_ids)


def test_league_create_without_tutorials(
    client, institution_headers, db_session
):
    """tutorial_ids is optional; omitting it creates a league with none."""
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={"name": "league_no_tutorials", "game": "greedy_pig"},
    )
    assert response.status_code == 200
    assert response.json()["tutorial_ids"] == []
    assert get_league_links(db_session, response.json()["league_id"]) == []


def test_league_create_unknown_tutorial_rolls_back(
    client, institution_headers, db_session
):
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "league_bad_tutorial",
            "game": "greedy_pig",
            "tutorial_ids": [99999],
        },
    )
    assert response.status_code == 404
    assert (
        db_session.exec(
            select(League).where(League.name == "league_bad_tutorial")
        ).first()
        is None
    )


def test_update_league_tutorials_replaces_set(
    client, institution_headers, db_session, tutorials
):
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "league_to_edit",
            "game": "greedy_pig",
            "tutorial_ids": [tutorials[0].id],
        },
    )
    league_id = response.json()["league_id"]

    response = client.post(
        "/institution/update-league-tutorials",
        headers=institution_headers,
        json={"league_id": league_id, "tutorial_ids": [tutorials[1].id]},
    )
    assert response.status_code == 200
    assert response.json()["tutorial_ids"] == [tutorials[1].id]
    assert get_league_links(db_session, league_id) == [tutorials[1].id]

    # Detach everything
    response = client.post(
        "/institution/update-league-tutorials",
        headers=institution_headers,
        json={"league_id": league_id, "tutorial_ids": []},
    )
    assert response.status_code == 200
    assert get_league_links(db_session, league_id) == []


def test_update_league_tutorials_unknown_tutorial(
    client, institution_headers, db_session, tutorials
):
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "league_bad_update",
            "game": "greedy_pig",
            "tutorial_ids": [tutorials[0].id],
        },
    )
    league_id = response.json()["league_id"]

    response = client.post(
        "/institution/update-league-tutorials",
        headers=institution_headers,
        json={"league_id": league_id, "tutorial_ids": [99999]},
    )
    assert response.status_code == 404
    # Attachments unchanged
    assert get_league_links(db_session, league_id) == [tutorials[0].id]


def test_league_tutorials_ownership(
    client, institution_headers, auth_headers, db_session, tutorials
):
    """An institution can't read or edit another institution's league; an
    admin can edit any league."""
    other_league = db_session.exec(
        select(League).where(League.name == "greedy_pig_league")
    ).one()  # owned by the seeded Admin Institution

    response = client.post(
        "/institution/get-league-tutorials",
        headers=institution_headers,
        json={"league_id": other_league.id},
    )
    assert response.status_code == 403

    response = client.post(
        "/institution/update-league-tutorials",
        headers=institution_headers,
        json={"league_id": other_league.id, "tutorial_ids": [tutorials[0].id]},
    )
    assert response.status_code == 403
    assert get_league_links(db_session, other_league.id) == []

    response = client.post(
        "/institution/update-league-tutorials",
        headers=auth_headers,
        json={"league_id": other_league.id, "tutorial_ids": [tutorials[0].id]},
    )
    assert response.status_code == 200
    assert get_league_links(db_session, other_league.id) == [tutorials[0].id]

    # Unknown league 404s
    response = client.post(
        "/institution/get-league-tutorials",
        headers=auth_headers,
        json={"league_id": 99999},
    )
    assert response.status_code == 404


def test_league_tutorials_role_gating(client, team_headers, tutorials):
    response = client.post(
        "/institution/get-league-tutorials",
        headers=team_headers,
        json={"league_id": 1},
    )
    assert response.status_code == 403

    response = client.post(
        "/institution/update-league-tutorials",
        headers=team_headers,
        json={"league_id": 1, "tutorial_ids": []},
    )
    assert response.status_code == 403


def test_delete_league_removes_attachments(
    client, institution_headers, db_session, tutorials
):
    response = client.post(
        "/institution/league-create",
        headers=institution_headers,
        json={
            "name": "league_to_delete",
            "game": "greedy_pig",
            "tutorial_ids": [t.id for t in tutorials],
        },
    )
    league_id = response.json()["league_id"]

    response = client.post(
        "/institution/delete-league",
        headers=institution_headers,
        json={"league_id": league_id},
    )
    assert response.status_code == 200
    assert get_league_links(db_session, league_id) == []
    # The tutorials themselves survive
    assert len(db_session.exec(select(Tutorial)).all()) == 2


def test_delete_tutorial_removes_attachments(
    client, auth_headers, db_session, tutorials
):
    league = db_session.exec(
        select(League).where(League.name == "greedy_pig_league")
    ).one()
    db_session.add(
        LeagueTutorial(league_id=league.id, tutorial_id=tutorials[0].id)
    )
    db_session.commit()

    response = client.delete(
        f"/tutorial/tutorial/{tutorials[0].id}", headers=auth_headers
    )
    assert response.status_code == 200
    assert get_league_links(db_session, league.id) == []
