"""Integration tests for POST /ai/assess-plagiarism.

All OpenAI calls are mocked via httpx patching — no real network calls.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session

from backend.database.db_models import (
    AIProviderKey,
    Institution,
    League,
    Submission,
    Team,
)
from backend.routes.auth.auth_core import create_access_token


# --- Fixtures ---


def _valid_llm_verdict_json():
    """A valid PlagiarismVerdict JSON blob (as a dict, not serialized)."""
    return {
        "progression_verdict": "organic",
        "progression_reasoning": "Small, incremental edits consistent with debugging.",
        "ai_generation_verdict": "unlikely",
        "ai_generation_reasoning": "Code style matches a typical student with inconsistent comments.",
        "overall_concern_level": "low",
        "specific_flags": [],
    }


def _llm_envelope(content_dict):
    """Wrap a content dict in the OpenAI chat completions envelope."""
    return {
        "choices": [
            {"message": {"content": json.dumps(content_dict)}}
        ]
    }


def _mock_openai_client(envelope):
    """Build a MagicMock that mimics httpx.AsyncClient returning the envelope."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value=envelope)
    mock_response.text = json.dumps(envelope)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.fixture
def institution_setup(db_session: Session):
    """Create an institution, league, team with 2 submissions, and an institution token.

    Returns (institution, league, team, headers).
    """
    institution = Institution(
        name="plagiarism_test_inst",
        contact_person="Test Person",
        contact_email="test@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    league = League(
        name="plagiarism_test_league",
        game="greedy_pig",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    team = Team(
        name="plagiarism_test_team",
        school_name="Test School",
        password_hash="hash",
        league_id=league.id,
        institution_id=institution.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Two submissions so the default path goes through _call_llm_full_assessment.
    base_ts = datetime.now(timezone.utc)
    for i, code in enumerate([
        "def foo():\n    return 1\n",
        "def foo():\n    return 2  # fixed\n",
    ]):
        db_session.add(
            Submission(
                code=code,
                timestamp=base_ts + timedelta(minutes=i * 5),
                team_id=team.id,
            )
        )
    db_session.commit()

    token = create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    headers = {"Authorization": f"Bearer {token}"}
    return institution, league, team, headers


@pytest.fixture
def stored_openai_key(db_session: Session):
    """Write an OpenAI key into the DB so the service doesn't raise NoApiKeyError."""
    key = AIProviderKey(provider="openai", api_key="sk-test-key-1234567890")
    db_session.add(key)
    db_session.commit()
    return key


# --- Tests ---


def test_assess_no_api_key_returns_error(client, institution_setup):
    """No API key configured → error response."""
    institution, league, team, headers = institution_setup
    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not configured" in data["message"].lower()


def test_assess_team_not_found_in_league(client, institution_setup, stored_openai_key):
    institution, league, team, headers = institution_setup
    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": "nonexistent_team"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()


def test_assess_league_not_owned_by_institution(
    client, institution_setup, stored_openai_key, db_session
):
    """Institution A cannot assess teams in Institution B's league."""
    institution_a, league_a, team_a, headers_a = institution_setup

    other_inst = Institution(
        name="other_inst",
        contact_person="Other",
        contact_email="other@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="hash",
    )
    db_session.add(other_inst)
    db_session.commit()
    db_session.refresh(other_inst)

    other_league = League(
        name="other_league",
        game="greedy_pig",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        institution_id=other_inst.id,
    )
    db_session.add(other_league)
    db_session.commit()
    db_session.refresh(other_league)

    # Institution A tries to assess in other_league (not owned).
    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers_a,
        json={"league_id": other_league.id, "team_name": team_a.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "permission" in data["message"].lower()


def test_assess_wrong_role_forbidden(client, institution_setup, stored_openai_key):
    """Student role is rejected by verify_admin_or_institution."""
    _, league, team, _ = institution_setup
    token = create_access_token(
        data={"sub": "some_student", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/ai/assess-plagiarism",
        headers={"Authorization": f"Bearer {token}"},
        json={"league_id": league.id, "team_name": team.name},
    )
    assert response.status_code == 403


def test_assess_no_submissions(
    client, institution_setup, stored_openai_key, db_session
):
    """Team with zero submissions → error."""
    institution, league, team, headers = institution_setup
    # Remove all existing submissions for the team.
    from sqlmodel import select
    subs = db_session.exec(
        select(Submission).where(Submission.team_id == team.id)
    ).all()
    for s in subs:
        db_session.delete(s)
    db_session.commit()

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "no submissions" in data["message"].lower()


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_two_submissions_happy_path(
    mock_client_cls, client, institution_setup, stored_openai_key
):
    institution, league, team, headers = institution_setup
    envelope = _llm_envelope(_valid_llm_verdict_json())
    mock_client_cls.return_value = _mock_openai_client(envelope)

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    report = data["data"]
    assert report["team_name"] == team.name
    assert report["league_id"] == league.id
    assert report["submission_count_total"] == 2
    assert report["submission_count_analyzed"] == 2
    assert report["sampled"] is False
    assert len(report["submission_metrics"]) == 2
    assert len(report["pairwise_metrics"]) == 1
    assert report["verdict"]["progression_verdict"] == "organic"
    assert report["model_used"] == "gpt-4o-mini"


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_single_submission_progression_not_applicable(
    mock_client_cls, client, institution_setup, stored_openai_key, db_session
):
    """Single submission → LLM returns not_applicable progression."""
    institution, league, team, headers = institution_setup
    # Delete one of the two submissions so only one remains.
    from sqlmodel import select
    subs = db_session.exec(
        select(Submission).where(Submission.team_id == team.id)
    ).all()
    db_session.delete(subs[1])
    db_session.commit()

    single_verdict = _valid_llm_verdict_json()
    single_verdict["progression_verdict"] = "not_applicable"
    single_verdict["progression_reasoning"] = "Only one submission; cannot assess progression."
    mock_client_cls.return_value = _mock_openai_client(
        _llm_envelope(single_verdict)
    )

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    report = data["data"]
    assert report["submission_count_total"] == 1
    assert report["submission_count_analyzed"] == 1
    assert len(report["pairwise_metrics"]) == 0
    assert report["verdict"]["progression_verdict"] == "not_applicable"


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_sampling_when_over_ten_submissions(
    mock_client_cls, client, institution_setup, stored_openai_key, db_session
):
    """Team with 15 submissions → sampled=True, analyzed=10."""
    institution, league, team, headers = institution_setup
    # Add 13 more submissions (starts with 2).
    base_ts = datetime.now(timezone.utc)
    for i in range(13):
        db_session.add(
            Submission(
                code=f"def foo():\n    return {i}\n",
                timestamp=base_ts + timedelta(hours=i + 10),
                team_id=team.id,
            )
        )
    db_session.commit()

    mock_client_cls.return_value = _mock_openai_client(
        _llm_envelope(_valid_llm_verdict_json())
    )

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    data = response.json()
    assert data["status"] == "success"
    report = data["data"]
    assert report["submission_count_total"] == 15
    assert report["submission_count_analyzed"] == 10
    assert report["sampled"] is True


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_llm_returns_non_json(
    mock_client_cls, client, institution_setup, stored_openai_key
):
    institution, league, team, headers = institution_setup
    envelope = {
        "choices": [{"message": {"content": "this is not json at all"}}]
    }
    mock_client_cls.return_value = _mock_openai_client(envelope)

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    data = response.json()
    assert data["status"] == "error"
    assert "malformed" in data["message"].lower() or "non-json" in data["message"].lower()


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_llm_returns_bad_literal(
    mock_client_cls, client, institution_setup, stored_openai_key
):
    """LLM returns JSON with an invalid enum value → Pydantic validation fails."""
    institution, league, team, headers = institution_setup
    bad_verdict = _valid_llm_verdict_json()
    bad_verdict["progression_verdict"] = "maybe"  # invalid literal
    mock_client_cls.return_value = _mock_openai_client(_llm_envelope(bad_verdict))

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    data = response.json()
    assert data["status"] == "error"
    assert "malformed" in data["message"].lower() or "schema" in data["message"].lower()


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_llm_extra_keys_rejected(
    mock_client_cls, client, institution_setup, stored_openai_key
):
    """extra='forbid' rejects hallucinated keys."""
    institution, league, team, headers = institution_setup
    bad_verdict = _valid_llm_verdict_json()
    bad_verdict["hallucinated_key"] = "surprise"
    mock_client_cls.return_value = _mock_openai_client(_llm_envelope(bad_verdict))

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    data = response.json()
    assert data["status"] == "error"


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_openai_500(
    mock_client_cls, client, institution_setup, stored_openai_key
):
    """Non-200 from OpenAI → error response."""
    institution, league, team, headers = institution_setup
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "internal server error"
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    data = response.json()
    assert data["status"] == "error"
    assert "500" in data["message"] or "malformed" in data["message"].lower()


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_openai_timeout(
    mock_client_cls, client, institution_setup, stored_openai_key
):
    import httpx as _httpx

    institution, league, team, headers = institution_setup
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=_httpx.TimeoutException("timed out"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    data = response.json()
    assert data["status"] == "error"
    assert "timed out" in data["message"].lower()


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_anonymization_strips_team_name(
    mock_client_cls, client, institution_setup, stored_openai_key
):
    """The team name must not appear in the outbound payload to OpenAI."""
    institution, league, team, headers = institution_setup
    mock_client = _mock_openai_client(_llm_envelope(_valid_llm_verdict_json()))
    mock_client_cls.return_value = mock_client

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    assert response.json()["status"] == "success"

    # Inspect the outbound request body.
    assert mock_client.post.call_count == 1
    call_args = mock_client.post.call_args
    # The body is passed as `json=...` kwarg.
    outbound_json = call_args.kwargs.get("json") or call_args.args[1]
    serialized = json.dumps(outbound_json)

    # Team name should NOT appear anywhere in the outbound payload.
    assert team.name not in serialized
    # School name should NOT appear either.
    assert "Test School" not in serialized
    # But the anonymized labels SHOULD appear.
    assert "submission_1" in serialized


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_deterministic_flag_over_likely_threshold(
    mock_client_cls, client, institution_setup, stored_openai_key, db_session
):
    """A submission delta exceeding 6 chars/sec should be flagged as likely_plagiarism
    regardless of the LLM verdict, and must be included in deterministic_flag_summary."""
    institution, league, team, headers = institution_setup
    # Wipe existing submissions and create a pair: 2000 chars added in 10 seconds = 200 cps.
    from sqlmodel import select
    for s in db_session.exec(select(Submission).where(Submission.team_id == team.id)).all():
        db_session.delete(s)
    db_session.commit()

    base = datetime.now(timezone.utc)
    db_session.add(Submission(code="x", timestamp=base, team_id=team.id))
    db_session.add(
        Submission(
            code="y" * 2000,
            timestamp=base + timedelta(seconds=10),
            team_id=team.id,
        )
    )
    db_session.commit()

    mock_client_cls.return_value = _mock_openai_client(
        _llm_envelope(_valid_llm_verdict_json())
    )

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    data = response.json()
    assert data["status"] == "success"
    report = data["data"]
    assert report["deterministic_concern_level"] == "likely_plagiarism"
    assert len(report["deterministic_flag_summary"]) == 1
    assert "most likely plagiarising" in report["deterministic_flag_summary"][0]
    # And it should also be on the per-pair metric.
    assert report["pairwise_metrics"][0]["deterministic_flag"] == "likely_plagiarism"
    assert report["pairwise_metrics"][0]["chars_added_per_second"] is not None


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_deterministic_flag_between_4_and_6(
    mock_client_cls, client, institution_setup, stored_openai_key, db_session
):
    """Delta in the probable-plagiarism range (4 < cps <= 6)."""
    institution, league, team, headers = institution_setup
    from sqlmodel import select
    for s in db_session.exec(select(Submission).where(Submission.team_id == team.id)).all():
        db_session.delete(s)
    db_session.commit()

    base = datetime.now(timezone.utc)
    # 500 chars in 100 seconds = 5 cps → probable
    db_session.add(Submission(code="x", timestamp=base, team_id=team.id))
    db_session.add(
        Submission(
            code="y" * 500,
            timestamp=base + timedelta(seconds=100),
            team_id=team.id,
        )
    )
    db_session.commit()

    mock_client_cls.return_value = _mock_openai_client(
        _llm_envelope(_valid_llm_verdict_json())
    )

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    data = response.json()
    assert data["status"] == "success"
    report = data["data"]
    assert report["deterministic_concern_level"] == "probable_plagiarism"
    assert "probably plagiarising" in report["deterministic_flag_summary"][0]
    assert report["pairwise_metrics"][0]["deterministic_flag"] == "probable_plagiarism"


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_normal_speed_no_deterministic_flag(
    mock_client_cls, client, institution_setup, stored_openai_key
):
    """Default institution_setup fixture uses 5-minute gaps → well under threshold."""
    institution, league, team, headers = institution_setup
    mock_client_cls.return_value = _mock_openai_client(
        _llm_envelope(_valid_llm_verdict_json())
    )

    response = client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    data = response.json()
    report = data["data"]
    assert report["deterministic_concern_level"] == "none"
    assert report["deterministic_flag_summary"] == []
    assert report["pairwise_metrics"][0]["deterministic_flag"] == "normal"


@patch("backend.routes.ai.plagiarism_service.httpx.AsyncClient")
def test_assess_deterministic_summary_sent_to_llm(
    mock_client_cls, client, institution_setup, stored_openai_key, db_session
):
    """The deterministic_flag_summary must be included in the outbound LLM payload."""
    institution, league, team, headers = institution_setup
    from sqlmodel import select
    for s in db_session.exec(select(Submission).where(Submission.team_id == team.id)).all():
        db_session.delete(s)
    db_session.commit()

    base = datetime.now(timezone.utc)
    db_session.add(Submission(code="x", timestamp=base, team_id=team.id))
    db_session.add(
        Submission(
            code="y" * 2000,
            timestamp=base + timedelta(seconds=10),
            team_id=team.id,
        )
    )
    db_session.commit()

    mock_client = _mock_openai_client(_llm_envelope(_valid_llm_verdict_json()))
    mock_client_cls.return_value = mock_client

    client.post(
        "/ai/assess-plagiarism",
        headers=headers,
        json={"league_id": league.id, "team_name": team.name},
    )
    call_args = mock_client.post.call_args
    outbound_json = call_args.kwargs.get("json") or call_args.args[1]
    # User message is the second element; parse its JSON content to inspect.
    user_msg_content = outbound_json["messages"][1]["content"]
    assert "deterministic_flag_summary" in user_msg_content
    assert "most likely plagiarising" in user_msg_content


def test_assess_admin_can_assess_any_league(
    client, institution_setup, stored_openai_key
):
    """Admin token bypasses institution ownership check."""
    institution, league, team, _ = institution_setup
    # Admin token — no institution_id needed; _resolve_institution returns (1, True)
    admin_token = create_access_token(
        data={"sub": "admin", "role": "admin"},
        expires_delta=timedelta(minutes=30),
    )
    with patch(
        "backend.routes.ai.plagiarism_service.httpx.AsyncClient"
    ) as mock_client_cls:
        mock_client_cls.return_value = _mock_openai_client(
            _llm_envelope(_valid_llm_verdict_json())
        )
        response = client.post(
            "/ai/assess-plagiarism",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"league_id": league.id, "team_name": team.name},
        )
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["team_name"] == team.name
