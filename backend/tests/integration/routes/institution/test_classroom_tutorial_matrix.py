"""GET /institution/classroom/{league_id}/tutorial-matrix: student x exercise
status grid per tutorial attached to the classroom."""


def test_matrix_success(client, classroom_setup):
    s = classroom_setup
    exercise_one, exercise_two, _ = s.exercises
    response = client.get(
        f"/institution/classroom/{s.league_a.id}/tutorial-matrix",
        headers=s.owner_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["league"] == {"id": s.league_a.id, "name": "classroom_9a"}
    # Rows in name order.
    assert [team["name"] for team in data["teams"]] == ["adam", "zoe"]

    # Only tutorial one is attached to 9a; tutorial two must not leak in.
    assert [tutorial["id"] for tutorial in data["tutorials"]] == [
        s.tutorial_one.id
    ]
    tutorial = data["tutorials"][0]
    assert tutorial["title"] == "Classroom Tutorial One"
    assert [exercise["id"] for exercise in tutorial["exercises"]] == [
        exercise_one.id,
        exercise_two.id,
    ]
    assert [exercise["order_index"] for exercise in tutorial["exercises"]] == [
        0,
        1,
    ]

    cells = {
        (cell["team_id"], cell["exercise_id"]): cell
        for cell in tutorial["cells"]
    }
    # adam failed once then passed exercise one: status passed, 2 attempts.
    adam_cell = cells[(s.adam.id, exercise_one.id)]
    assert adam_cell["status"] == "passed"
    assert adam_cell["attempts"] == 2
    assert adam_cell["last_attempt_at"] is not None
    # zoe's attempt never ran: attempted, 1 attempt.
    zoe_cell = cells[(s.zoe.id, exercise_one.id)]
    assert zoe_cell["status"] == "attempted"
    assert zoe_cell["attempts"] == 1
    # Untouched cells are omitted: nobody touched exercise two.
    assert set(cells) == {
        (s.adam.id, exercise_one.id),
        (s.zoe.id, exercise_one.id),
    }


def test_matrix_league_without_tutorials(client, classroom_setup):
    s = classroom_setup
    response = client.get(
        f"/institution/classroom/{s.rival_league.id}/tutorial-matrix",
        headers=s.rival_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tutorials"] == []
    assert [team["name"] for team in data["teams"]] == ["rival_student"]


def test_matrix_access_control(client, team_headers, classroom_setup):
    s = classroom_setup
    url = f"/institution/classroom/{s.league_a.id}/tutorial-matrix"

    assert client.get(url).status_code == 401
    assert client.get(url, headers=s.rival_headers).status_code == 403
    assert client.get(url, headers=team_headers).status_code == 403
    assert (
        client.get(
            "/institution/classroom/999999/tutorial-matrix",
            headers=s.owner_headers,
        ).status_code
        == 404
    )


def test_matrix_admin_bypass(client, auth_headers, classroom_setup):
    s = classroom_setup
    response = client.get(
        f"/institution/classroom/{s.league_a.id}/tutorial-matrix",
        headers=auth_headers,
    )
    assert response.status_code == 200
