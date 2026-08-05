"""GET /diagnostics/pyodide-fallbacks — the fallback-telemetry read side.

This endpoint outlives backend/fallback_lambda/: validation fallbacks
(validation:-prefixed reasons from /user/submit-agent) keep feeding the same
Valkey counters after the exercise fallback is deleted.
"""

from backend.time_utils import utc_now


def _today() -> str:
    return utc_now().strftime("%Y-%m-%d")


def test_admin_reads_fallback_stats(client, admin_headers, valkey):
    valkey.incr(f"pyodide-fallback:count:{_today()}")
    valkey.incr(f"pyodide-fallback:count:{_today()}")
    valkey.hincrby(f"pyodide-fallback:reasons:{_today()}", "boot-timeout", 2)

    response = client.get(
        "/diagnostics/pyodide-fallbacks", headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["days"] == [
        {
            "date": _today(),
            "count": 2,
            "reasons": {"boot-timeout": 2},
        }
    ]

    # Students may not read diagnostics
    response = client.get("/diagnostics/pyodide-fallbacks")
    assert response.status_code == 401
