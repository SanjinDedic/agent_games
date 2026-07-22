"""GET /institution/classroom/{league_id}/progress: per-student roster stats
for one classroom (lifetime agent stats, ranking trend, last-active across
agent + exercise activity, exercise completion vs attached tutorials)."""

from datetime import timedelta

from backend.routes.auth.auth_core import create_access_token
from backend.routes.institution.classroom_db import RANKING_HISTORY_LIMIT
from backend.tests.conftest import add_submission
from backend.time_utils import utc_now


def test_classroom_progress_success(client, classroom_setup):
    s = classroom_setup
    response = client.get(
        f"/institution/classroom/{s.league_a.id}/progress",
        headers=s.owner_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["league"]["id"] == s.league_a.id
    assert data["league"]["name"] == "classroom_9a"
    assert data["league"]["game"] == "greedy_pig"
    assert data["league"]["signup_link"] is None

    # Only league_a's students, ordered by name (zoe has the lower id).
    assert [team["name"] for team in data["teams"]] == ["adam", "zoe"]
    adam, zoe = data["teams"]

    assert adam["total_attempts"] == 6
    assert adam["validated_submissions"] == 5
    assert adam["hints_used"] == 1
    assert adam["achieved_first"] is True
    # Full history oldest -> newest with timestamps, not just the last 3.
    assert [entry["ranking"] for entry in adam["ranking_history"]] == [1, 4, 3, 2]
    assert all(entry["timestamp"] for entry in adam["ranking_history"])
    # Exercise counts are scoped to tutorial one (attached to 9a): the passed
    # run on tutorial two's exercise must not count here...
    assert adam["exercises_total"] == 2
    assert adam["exercises_attempted"] == 1
    assert adam["exercises_passed"] == 1
    # ...but it IS adam's newest activity, so last_active comes from it and
    # is newer than his latest agent submission.
    assert adam["latest_agent_submission"] is not None
    assert adam["latest_exercise_activity"] is not None
    assert adam["last_active"] == adam["latest_exercise_activity"]
    assert adam["last_active"] > adam["latest_agent_submission"]

    assert zoe["total_attempts"] == 0
    assert zoe["validated_submissions"] == 0
    assert zoe["hints_used"] == 0
    assert zoe["ranking_history"] == []
    assert zoe["achieved_first"] is False
    assert zoe["latest_agent_submission"] is None
    # zoe's metadata-only attempt counts as attempted and as activity.
    assert zoe["exercises_attempted"] == 1
    assert zoe["exercises_passed"] == 0
    assert zoe["last_active"] == zoe["latest_exercise_activity"]


def test_classroom_progress_league_without_tutorials(client, classroom_setup):
    """rival league has no tutorials and no submissions: zeroed rows."""
    s = classroom_setup
    response = client.get(
        f"/institution/classroom/{s.rival_league.id}/progress",
        headers=s.rival_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert [team["name"] for team in data["teams"]] == ["rival_student"]
    row = data["teams"][0]
    assert row["exercises_total"] == 0
    assert row["exercises_attempted"] == 0
    assert row["last_active"] is None


def test_classroom_progress_ranking_history_cap(
    client, db_session, classroom_setup
):
    """More ranked submissions than the cap: newest RANKING_HISTORY_LIMIT
    entries survive (oldest -> newest), and achieved_first still sees the
    rank-1 run that fell outside the window."""
    s = classroom_setup
    base = utc_now()
    # Oldest submission is the only rank 1; everything after is rank 2.
    add_submission(
        db_session,
        code="old first place",
        timestamp=base - timedelta(hours=2),
        team_id=s.zoe.id,
        league_id=s.league_a.id,
        ranking=1,
    )
    for i in range(RANKING_HISTORY_LIMIT):
        add_submission(
            db_session,
            code=f"ranked {i}",
            timestamp=base - timedelta(minutes=RANKING_HISTORY_LIMIT - i),
            team_id=s.zoe.id,
            league_id=s.league_a.id,
            ranking=2,
        )
    db_session.commit()

    response = client.get(
        f"/institution/classroom/{s.league_a.id}/progress",
        headers=s.owner_headers,
    )
    assert response.status_code == 200
    zoe = next(
        team for team in response.json()["teams"] if team["name"] == "zoe"
    )
    history = zoe["ranking_history"]
    assert len(history) == RANKING_HISTORY_LIMIT
    assert all(entry["ranking"] == 2 for entry in history)
    timestamps = [entry["timestamp"] for entry in history]
    assert timestamps == sorted(timestamps)
    assert zoe["achieved_first"] is True


def test_classroom_progress_access_control(client, classroom_setup):
    s = classroom_setup
    url = f"/institution/classroom/{s.league_a.id}/progress"

    # No token
    assert client.get(url).status_code == 401

    # Another institution's token
    response = client.get(url, headers=s.rival_headers)
    assert response.status_code == 403

    # Unknown league
    response = client.get(
        "/institution/classroom/999999/progress", headers=s.owner_headers
    )
    assert response.status_code == 404

    # Institution token without an institution id
    incomplete_token = create_access_token(
        data={"sub": "classroom_owner", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.get(
        url, headers={"Authorization": f"Bearer {incomplete_token}"}
    )
    assert response.status_code == 400


def test_classroom_progress_team_token_rejected(
    client, team_headers, classroom_setup
):
    response = client.get(
        f"/institution/classroom/{classroom_setup.league_a.id}/progress",
        headers=team_headers,
    )
    assert response.status_code == 403


def test_classroom_progress_admin_bypass(client, auth_headers, classroom_setup):
    """Admin tokens may read any institution's classroom."""
    s = classroom_setup
    response = client.get(
        f"/institution/classroom/{s.league_a.id}/progress", headers=auth_headers
    )
    assert response.status_code == 200
    assert [team["name"] for team in response.json()["teams"]] == ["adam", "zoe"]
