"""Unit tests for admin_backup.py — mocked S3 and subprocess calls."""

import os
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from botocore.exceptions import ClientError
from backend.time_utils import utc_now


# ─── _parse_db_url ────────────────────────────────────────────────────────────

@patch("backend.routes.admin.admin_backup.get_database_url")
def test_parse_db_url_standard(mock_url):
    """Parses a standard postgresql+psycopg URL."""
    mock_url.return_value = "postgresql+psycopg://myuser:mypass@dbhost:5433/mydb"
    from backend.routes.admin.admin_backup import _parse_db_url

    result = _parse_db_url()
    assert result["host"] == "dbhost"
    assert result["port"] == "5433"
    assert result["user"] == "myuser"
    assert result["password"] == "mypass"
    assert result["dbname"] == "mydb"


@patch("backend.routes.admin.admin_backup.get_database_url")
def test_parse_db_url_defaults(mock_url):
    """Falls back to defaults when components are missing."""
    mock_url.return_value = "postgresql+psycopg:///testdb"
    from backend.routes.admin.admin_backup import _parse_db_url

    result = _parse_db_url()
    assert result["host"] == "localhost"
    assert result["port"] == "5432"
    assert result["user"] == "postgres"
    assert result["password"] == ""
    assert result["dbname"] == "testdb"


# ─── _get_s3_client ──────────────────────────────────────────────────────────

def test_get_s3_client_missing_key():
    """Raises ValueError when AWS_ACCESS_KEY_ID is missing."""
    from backend.routes.admin.admin_backup import _get_s3_client

    env = {k: v for k, v in os.environ.items() if k not in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="Missing AWS credentials"):
            _get_s3_client()


def test_get_s3_client_missing_secret():
    """Raises ValueError when AWS_SECRET_ACCESS_KEY is missing."""
    from backend.routes.admin.admin_backup import _get_s3_client

    env = {"AWS_ACCESS_KEY_ID": "test_key"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="Missing AWS credentials"):
            _get_s3_client()


# ─── create_backup ────────────────────────────────────────────────────────────

@patch("backend.routes.admin.admin_backup._get_s3_client")
@patch("backend.routes.admin.admin_backup.subprocess.run")
@patch("backend.routes.admin.admin_backup._parse_db_url")
def test_create_backup_success(mock_parse, mock_run, mock_s3):
    """Successful backup: pg_dump + S3 upload."""
    from backend.routes.admin.admin_backup import create_backup

    mock_parse.return_value = {
        "host": "localhost", "port": "5432",
        "user": "postgres", "password": "pass", "dbname": "testdb",
    }
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    mock_s3.return_value = MagicMock()

    # Patch os.path.getsize to return a fake size
    with patch("backend.routes.admin.admin_backup.os.path.getsize", return_value=12345):
        result = create_backup()

    assert "filename" in result
    assert result["filename"].startswith("agent_games_")
    assert result["filename"].endswith(".dump")
    assert result["s3_key"].startswith("backups/")
    assert result["size_bytes"] == 12345
    assert "timestamp" in result

    # pg_dump was called in custom format with zstd compression
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "pg_dump" in cmd
    assert "--format=custom" in cmd
    assert "--compress=zstd:3" in cmd

    # S3 upload was called
    mock_s3.return_value.upload_file.assert_called_once()


@patch("backend.routes.admin.admin_backup._parse_db_url")
@patch("backend.routes.admin.admin_backup.subprocess.run")
def test_create_backup_pgdump_fails(mock_run, mock_parse):
    """RuntimeError when pg_dump returns non-zero."""
    from backend.routes.admin.admin_backup import create_backup

    mock_parse.return_value = {
        "host": "localhost", "port": "5432",
        "user": "postgres", "password": "", "dbname": "testdb",
    }
    mock_run.return_value = MagicMock(returncode=1, stderr="connection refused")

    with pytest.raises(RuntimeError, match="pg_dump failed"):
        create_backup()


@patch("backend.routes.admin.admin_backup._get_s3_client")
@patch("backend.routes.admin.admin_backup.subprocess.run")
@patch("backend.routes.admin.admin_backup._parse_db_url")
def test_create_backup_s3_upload_fails(mock_parse, mock_run, mock_s3):
    """RuntimeError when S3 upload fails."""
    from backend.routes.admin.admin_backup import create_backup

    mock_parse.return_value = {
        "host": "localhost", "port": "5432",
        "user": "postgres", "password": "", "dbname": "testdb",
    }
    mock_run.return_value = MagicMock(returncode=0)
    mock_s3.return_value.upload_file.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "denied"}}, "upload_file"
    )

    with patch("backend.routes.admin.admin_backup.os.path.getsize", return_value=100):
        with pytest.raises(RuntimeError, match="Failed to upload to S3"):
            create_backup()


@patch("backend.routes.admin.admin_backup._get_s3_client")
@patch("backend.routes.admin.admin_backup.subprocess.run")
@patch("backend.routes.admin.admin_backup._parse_db_url")
def test_create_backup_label_in_filename(mock_parse, mock_run, mock_s3):
    """The label is embedded in the backup filename."""
    from backend.routes.admin.admin_backup import create_backup

    mock_parse.return_value = {
        "host": "localhost", "port": "5432",
        "user": "postgres", "password": "", "dbname": "testdb",
    }
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    mock_s3.return_value = MagicMock()

    with patch("backend.routes.admin.admin_backup.os.path.getsize", return_value=1):
        assert "_PRE_DEPLOY_" in create_backup(label="PRE_DEPLOY")["filename"]
        assert "_DAILY_" in create_backup(label="DAILY")["filename"]
        # Default label marks manual backups
        assert "_MANUAL_" in create_backup()["filename"]


# ─── prune_backups ────────────────────────────────────────────────────────────

@patch("backend.routes.admin.admin_backup._get_s3_client")
def test_prune_backups_deletes_only_expired(mock_s3):
    """Backups past the cutoff are deleted; recent ones and foreign keys survive."""
    from datetime import datetime, timedelta, timezone

    from backend.routes.admin.admin_backup import prune_backups

    now = utc_now()
    mock_s3.return_value.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "backups/agent_games_DAILY_old.sql", "Size": 1,
             "LastModified": now - timedelta(days=61)},
            {"Key": "backups/agent_games_DAILY_new.sql", "Size": 1,
             "LastModified": now - timedelta(days=1)},
            # Non-backup object under the prefix must never be touched
            {"Key": "backups/unrelated_file.txt", "Size": 1,
             "LastModified": now - timedelta(days=365)},
        ]
    }

    deleted = prune_backups(days=60)

    assert deleted == ["backups/agent_games_DAILY_old.sql"]
    mock_s3.return_value.delete_objects.assert_called_once()
    delete_arg = mock_s3.return_value.delete_objects.call_args.kwargs["Delete"]
    assert delete_arg["Objects"] == [{"Key": "backups/agent_games_DAILY_old.sql"}]


@patch("backend.routes.admin.admin_backup._get_s3_client")
def test_prune_backups_nothing_expired(mock_s3):
    """No delete call when everything is within the retention window."""
    from datetime import datetime, timedelta, timezone

    from backend.routes.admin.admin_backup import prune_backups

    now = utc_now()
    mock_s3.return_value.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "backups/agent_games_DAILY_new.sql", "Size": 1,
             "LastModified": now - timedelta(days=59)},
        ]
    }

    assert prune_backups(days=60) == []
    mock_s3.return_value.delete_objects.assert_not_called()


# ─── list_backups ─────────────────────────────────────────────────────────────

@patch("backend.routes.admin.admin_backup._get_s3_client")
def test_list_backups_success(mock_s3):
    """Returns sorted list of backups, most recent first."""
    from backend.routes.admin.admin_backup import list_backups
    from datetime import datetime

    mock_s3.return_value.list_objects_v2.return_value = {
        "Contents": [
            {
                "Key": "backups/agent_games_20260101_000000.sql",
                "Size": 1000,
                "LastModified": datetime(2026, 1, 1),
            },
            {
                "Key": "backups/agent_games_20260201_000000.sql",
                "Size": 2000,
                "LastModified": datetime(2026, 2, 1),
            },
        ]
    }

    result = list_backups()
    assert len(result) == 2
    # Most recent first
    assert result[0]["filename"] == "agent_games_20260201_000000.sql"
    assert result[1]["filename"] == "agent_games_20260101_000000.sql"
    assert result[0]["size_bytes"] == 2000


@patch("backend.routes.admin.admin_backup._get_s3_client")
def test_list_backups_empty(mock_s3):
    """Empty bucket returns empty list."""
    from backend.routes.admin.admin_backup import list_backups

    mock_s3.return_value.list_objects_v2.return_value = {}

    result = list_backups()
    assert result == []


# ─── restore_backup ───────────────────────────────────────────────────────────

@patch("backend.routes.admin.admin_backup._get_s3_client")
@patch("backend.routes.admin.admin_backup.subprocess.run")
@patch("backend.routes.admin.admin_backup._parse_db_url")
def test_restore_backup_success(mock_parse, mock_run, mock_s3):
    """Custom-format restore downloads, drops, creates, and runs pg_restore."""
    from backend.routes.admin.admin_backup import restore_backup

    mock_parse.return_value = {
        "host": "localhost", "port": "5432",
        "user": "postgres", "password": "pass", "dbname": "testdb",
    }
    # All subprocess calls succeed
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    mock_s3.return_value = MagicMock()

    result = restore_backup("backups/agent_games_20260101_000000.dump")

    assert result["filename"] == "agent_games_20260101_000000.dump"
    assert result["s3_key"] == "backups/agent_games_20260101_000000.dump"

    # S3 download was called
    mock_s3.return_value.download_file.assert_called_once()

    # subprocess.run called 4 times: terminate, drop, create, restore
    assert mock_run.call_count == 4

    # The final call restores the archive with pg_restore
    restore_cmd = mock_run.call_args_list[-1][0][0]
    assert restore_cmd[0] == "pg_restore"
    assert "--no-owner" in restore_cmd


@patch("backend.routes.admin.admin_backup._get_s3_client")
@patch("backend.routes.admin.admin_backup.subprocess.run")
@patch("backend.routes.admin.admin_backup._parse_db_url")
def test_restore_backup_legacy_sql(mock_parse, mock_run, mock_s3):
    """Legacy .sql backups still restore via psql -f."""
    from backend.routes.admin.admin_backup import restore_backup

    mock_parse.return_value = {
        "host": "localhost", "port": "5432",
        "user": "postgres", "password": "pass", "dbname": "testdb",
    }
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    mock_s3.return_value = MagicMock()

    result = restore_backup("backups/agent_games_20260101_000000.sql")

    assert result["filename"] == "agent_games_20260101_000000.sql"
    assert mock_run.call_count == 4

    restore_cmd = mock_run.call_args_list[-1][0][0]
    assert restore_cmd[0] == "psql"
    assert "-f" in restore_cmd


@patch("backend.routes.admin.admin_backup._get_s3_client")
@patch("backend.routes.admin.admin_backup.subprocess.run")
@patch("backend.routes.admin.admin_backup._parse_db_url")
def test_restore_backup_drop_fails(mock_parse, mock_run, mock_s3):
    """RuntimeError when DROP DATABASE fails."""
    from backend.routes.admin.admin_backup import restore_backup

    mock_parse.return_value = {
        "host": "localhost", "port": "5432",
        "user": "postgres", "password": "", "dbname": "testdb",
    }
    mock_s3.return_value = MagicMock()

    # First call (terminate) succeeds, second (drop) fails
    mock_run.side_effect = [
        MagicMock(returncode=0),  # terminate connections
        MagicMock(returncode=1, stderr="permission denied"),  # drop
    ]

    with pytest.raises(RuntimeError, match="DROP DATABASE failed"):
        restore_backup("backups/test.sql")
