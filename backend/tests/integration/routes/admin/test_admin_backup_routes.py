"""Integration tests for backup API endpoints — testing auth/routing with mocked backup functions."""

from datetime import timedelta
from unittest.mock import patch

import pytest

from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def admin_headers() -> dict:
    token = create_access_token(
        data={"sub": "admin", "role": "admin"},
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def student_headers() -> dict:
    token = create_access_token(
        data={"sub": "student", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@patch("backend.routes.admin.admin_router.create_backup")
def test_backup_database_success(mock_backup, client, admin_headers):
    """Admin can trigger a backup."""
    mock_backup.return_value = {
        "filename": "agent_games_20260404.sql",
        "s3_key": "backups/agent_games_20260404.sql",
        "bucket": "agent-games-backups",
        "size_bytes": 50000,
        "timestamp": "20260404_120000",
    }
    resp = client.post("/admin/backup-database", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["data"]["filename"] == "agent_games_20260404.sql"
    mock_backup.assert_called_once()


def test_backup_database_no_auth(client):
    """No token returns 401."""
    resp = client.post("/admin/backup-database")
    assert resp.status_code == 401


def test_backup_database_wrong_role(client, student_headers):
    """Non-admin role returns 403."""
    resp = client.post("/admin/backup-database", headers=student_headers)
    assert resp.status_code == 403


@patch("backend.routes.admin.admin_router.list_backups")
def test_list_backups_success(mock_list, client, admin_headers):
    """Admin can list backups."""
    mock_list.return_value = [
        {
            "filename": "agent_games_20260404.sql",
            "s3_key": "backups/agent_games_20260404.sql",
            "size_bytes": 50000,
            "last_modified": "2026-04-04T12:00:00",
        }
    ]
    resp = client.get("/admin/list-backups", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "1 backup" in data["message"]
    assert len(data["data"]["backups"]) == 1
    mock_list.assert_called_once()


def test_list_backups_wrong_role(client, student_headers):
    """Non-admin role returns 403."""
    resp = client.get("/admin/list-backups", headers=student_headers)
    assert resp.status_code == 403


@patch("backend.routes.admin.admin_router.restore_backup")
def test_restore_database_success(mock_restore, client, admin_headers):
    """Admin can trigger a restore."""
    mock_restore.return_value = {
        "filename": "agent_games_20260404.sql",
        "s3_key": "backups/agent_games_20260404.sql",
    }
    resp = client.post(
        "/admin/restore-database",
        headers=admin_headers,
        json={"s3_key": "backups/agent_games_20260404.sql"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    mock_restore.assert_called_once_with("backups/agent_games_20260404.sql")


def test_restore_database_wrong_role(client, student_headers):
    """Non-admin role returns 403."""
    resp = client.post(
        "/admin/restore-database",
        headers=student_headers,
        json={"s3_key": "backups/test.sql"},
    )
    assert resp.status_code == 403
