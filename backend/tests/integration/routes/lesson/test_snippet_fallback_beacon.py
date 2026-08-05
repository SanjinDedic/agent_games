"""Integration tests for POST /lesson/snippet-fallback-beacon.

Snippets run via the direct Lambda Function URL have no result to persist,
so the browser fires this beacon purely to keep the pyodide-fallback
telemetry honest. It executes nothing and shares run-snippet's 10/min
Valkey budget so spam can't inflate the counters.
"""

import pytest

import backend.routes.lesson.lesson_db as lesson_db
from backend.time_utils import utc_now


def _today() -> str:
    return utc_now().strftime("%Y-%m-%d")


@pytest.fixture(autouse=True)
def reset_snippet_rate_limit():
    """Same leak guard as test_lesson_router: budgets live in Valkey with a
    60s window, so counts bleed across tests unless cleared."""
    try:
        client = lesson_db._get_rate_limit_client()
        keys = list(client.scan_iter("lesson-snippet-rate:*"))
        if keys:
            client.delete(*keys)
    except Exception:  # noqa: BLE001 - valkey down fails the beacon tests anyway
        pass
    yield


def test_beacon_is_counted_with_snippet_prefix(client, team_headers, valkey):
    response = client.post(
        "/lesson/snippet-fallback-beacon",
        json={"reason": "boot-timeout"},
        headers=team_headers,
    )
    assert response.status_code == 200
    assert valkey.get(f"pyodide-fallback:count:{_today()}") == "1"
    assert valkey.hgetall(f"pyodide-fallback:reasons:{_today()}") == {
        "snippet:boot-timeout": "1"
    }


def test_missing_reason_is_unspecified(client, team_headers, valkey):
    response = client.post(
        "/lesson/snippet-fallback-beacon", json={}, headers=team_headers
    )
    assert response.status_code == 200
    assert valkey.hgetall(f"pyodide-fallback:reasons:{_today()}") == {
        "snippet:unspecified": "1"
    }


def test_beacon_shares_run_snippet_budget(
    client, team_headers, valkey, monkeypatch
):
    """The beacon consumes the same fixed-window counter as /run-snippet."""
    monkeypatch.setattr(lesson_db, "SNIPPET_RUNS_PER_MINUTE", 2)
    for _ in range(2):
        assert (
            client.post(
                "/lesson/snippet-fallback-beacon",
                json={"reason": "boot-timeout"},
                headers=team_headers,
            ).status_code
            == 200
        )
    response = client.post(
        "/lesson/snippet-fallback-beacon",
        json={"reason": "boot-timeout"},
        headers=team_headers,
    )
    assert response.status_code == 429
    # Only the allowed beacons were counted
    assert valkey.hgetall(f"pyodide-fallback:reasons:{_today()}") == {
        "snippet:boot-timeout": "2"
    }

    # And the beacon budget really is run-snippet's: the next run is 429 too
    response = client.post(
        "/lesson/run-snippet",
        json={"code": "print(1)"},
        headers=team_headers,
    )
    assert response.status_code == 429


def test_requires_auth(client):
    assert (
        client.post(
            "/lesson/snippet-fallback-beacon", json={"reason": "x"}
        ).status_code
        == 401
    )
