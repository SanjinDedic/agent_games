"""Unit tests for pyodide_support's row normalization and stats shaping."""

from unittest.mock import MagicMock, patch

from backend.routes.tutorial.pyodide_support import (
    ROW_KEYS,
    get_pyodide_fallback_stats,
    normalize_client_rows,
)


def test_normalize_keeps_only_contract_keys_and_stamps_source():
    rows = normalize_client_rows(
        [
            {
                "name": "adds",
                "call": "add(1, 2)",
                "expected": 3,
                "actual": "3",
                "passed": 1,
                "error": None,
                "source": "spoofed",
                "extra": "dropped",
            }
        ],
        "pyodide",
    )
    assert rows == [
        {
            "name": "adds",
            "call": None,
            "expected": 3,
            "actual": "3",
            "passed": True,
            "error": None,
            "source": "pyodide",
        }
    ]


def test_normalize_drops_non_dict_rows_and_fills_missing_keys():
    rows = normalize_client_rows(["junk", 42, {}], "celery_fallback")
    assert len(rows) == 1
    (row,) = rows
    assert set(row) == set(ROW_KEYS) | {"source"}
    assert row["passed"] is False
    assert row["source"] == "celery_fallback"


def test_normalize_empty_input():
    assert normalize_client_rows([], "pyodide") == []


def test_stats_shape_skips_zero_days():
    client = MagicMock()
    client.get.side_effect = ["3", None] + [None] * 12
    client.hgetall.return_value = {"boot-timeout": "2", "boot-fetch-failed": "1"}

    with patch(
        "backend.routes.tutorial.pyodide_support._get_valkey_client",
        return_value=client,
    ):
        stats = get_pyodide_fallback_stats(days=14)

    assert stats["total"] == 3
    (day,) = stats["days"]
    assert day["count"] == 3
    assert day["reasons"] == {"boot-timeout": 2, "boot-fetch-failed": 1}
    # Only the nonzero day triggered a reasons lookup
    assert client.hgetall.call_count == 1


def test_stats_fail_open():
    import redis

    with patch(
        "backend.routes.tutorial.pyodide_support._get_valkey_client",
        side_effect=redis.RedisError("down"),
    ):
        stats = get_pyodide_fallback_stats()

    assert stats["days"] == []
    assert stats["total"] == 0
    assert "error" in stats
