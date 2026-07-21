"""The student drill-down endpoints: /institution/student/{team_id}/summary,
/agent-submissions and /exercise-submissions."""


def test_student_summary(client, classroom_setup):
    s = classroom_setup
    exercise_one, exercise_two, _ = s.exercises
    response = client.get(
        f"/institution/student/{s.adam.id}/summary", headers=s.owner_headers
    )
    assert response.status_code == 200
    data = response.json()

    assert data["team"]["id"] == s.adam.id
    assert data["team"]["name"] == "adam"
    assert data["team"]["school"] == "Greenfield High"
    assert data["team"]["league_id"] == s.league_a.id
    assert data["team"]["league_name"] == "classroom_9a"
    assert data["team"]["created_at"] is not None

    agent = data["agent"]
    assert agent["total_attempts"] == 6
    assert agent["validated_submissions"] == 5
    assert agent["hints_used"] == 1
    assert agent["achieved_first"] is True
    assert [entry["ranking"] for entry in agent["ranking_history"]] == [1, 4, 3, 2]

    # Newest activity is the out-of-classroom exercise run.
    assert data["last_active"] > agent["latest_submission"]

    # Tutorials of the CURRENT league only, untouched exercises included.
    assert [tutorial["id"] for tutorial in data["tutorials"]] == [
        s.tutorial_one.id
    ]
    exercises = {
        exercise["id"]: exercise
        for exercise in data["tutorials"][0]["exercises"]
    }
    assert exercises[exercise_one.id]["status"] == "passed"
    assert exercises[exercise_one.id]["attempts"] == 2
    assert exercises[exercise_two.id]["status"] == "untouched"
    assert exercises[exercise_two.id]["attempts"] == 0
    assert exercises[exercise_two.id]["last_attempt_at"] is None


def test_student_agent_submissions(client, classroom_setup):
    s = classroom_setup
    response = client.get(
        f"/institution/student/{s.adam.id}/agent-submissions",
        headers=s.owner_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["team"] == {"id": s.adam.id, "name": "adam"}
    submissions = data["submissions"]
    # 5 validated submissions (the failed attempt has no code row), oldest
    # first, with ranking and league carried through.
    assert len(submissions) == 5
    assert [sub["ranking"] for sub in submissions] == [1, 4, 3, 2, None]
    assert submissions[0]["code"] == "ranked agent (1)"
    assert submissions[-1]["code"] == "hinted agent"
    assert submissions[-1]["duration_ms"] == 321.0
    assert all(sub["league_id"] == s.league_a.id for sub in submissions)
    timestamps = [sub["timestamp"] for sub in submissions]
    assert timestamps == sorted(timestamps)


def test_student_exercise_submissions(client, classroom_setup):
    s = classroom_setup
    exercise_one, _, _ = s.exercises
    response = client.get(
        f"/institution/student/{s.adam.id}/exercise-submissions"
        f"?exercise_id={exercise_one.id}",
        headers=s.owner_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["team"] == {"id": s.adam.id, "name": "adam"}
    assert data["exercise"] == {
        "id": exercise_one.id,
        "title": "Exercise One",
        "tutorial_id": s.tutorial_one.id,
        "tutorial_title": "Classroom Tutorial One",
    }
    submissions = data["submissions"]
    # Newest first: the passing run, then the failing one, with code and
    # per-test results.
    assert len(submissions) == 2
    assert submissions[0]["passed"] is True
    assert submissions[0]["code"] == "def solve(): return 1"
    assert submissions[0]["test_results"] == [
        {"name": "test_basic", "passed": True}
    ]
    assert submissions[1]["passed"] is False
    assert submissions[1]["test_results"] == [
        {"name": "test_basic", "passed": False}
    ]


def test_student_exercise_submissions_requires_exercise_id(
    client, classroom_setup
):
    s = classroom_setup
    response = client.get(
        f"/institution/student/{s.adam.id}/exercise-submissions",
        headers=s.owner_headers,
    )
    assert response.status_code == 422


def test_student_exercise_submissions_unknown_exercise(client, classroom_setup):
    s = classroom_setup
    response = client.get(
        f"/institution/student/{s.adam.id}/exercise-submissions"
        f"?exercise_id=999999",
        headers=s.owner_headers,
    )
    assert response.status_code == 404


def test_student_endpoints_access_control(
    client, team_headers, classroom_setup
):
    """Teacher A cannot read teacher B's student; team tokens and unknown
    teams are rejected on every student endpoint."""
    s = classroom_setup
    exercise_one, _, _ = s.exercises
    urls = [
        f"/institution/student/{s.adam.id}/summary",
        f"/institution/student/{s.adam.id}/agent-submissions",
        f"/institution/student/{s.adam.id}/exercise-submissions"
        f"?exercise_id={exercise_one.id}",
    ]
    for url in urls:
        assert client.get(url).status_code == 401
        assert client.get(url, headers=s.rival_headers).status_code == 403
        assert client.get(url, headers=team_headers).status_code == 403

    for suffix in (
        "summary",
        "agent-submissions",
        f"exercise-submissions?exercise_id={exercise_one.id}",
    ):
        response = client.get(
            f"/institution/student/999999/{suffix}", headers=s.owner_headers
        )
        assert response.status_code == 404


def test_student_endpoints_admin_bypass(client, auth_headers, classroom_setup):
    s = classroom_setup
    response = client.get(
        f"/institution/student/{s.adam.id}/summary", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["team"]["name"] == "adam"
