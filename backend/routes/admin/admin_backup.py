import logging
import os
import subprocess
import tempfile
from datetime import datetime
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from backend.database.db_config import get_database_url

logger = logging.getLogger(__name__)


def _parse_db_url():
    """Extract host, port, user, password, dbname from the SQLAlchemy DATABASE_URL."""
    raw = get_database_url()
    # Strip the +psycopg driver so urlparse handles it cleanly
    raw = raw.replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(raw)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/"),
    }


def _get_s3_client():
    """Build a boto3 S3 client for AWS."""
    key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    region = os.environ.get("AWS_REGION", "ap-southeast-2")
    if not all([key, secret]):
        raise ValueError(
            "Missing AWS credentials. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
        )
    return boto3.client(
        "s3",
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        region_name=region,
    )


def create_backup() -> dict:
    """Run pg_dump and upload the .sql file to AWS S3.

    Returns a dict with backup metadata on success.
    """
    bucket = os.environ.get("AWS_S3_BUCKET", "agent-games-backups")
    db = _parse_db_url()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"agent_games_{timestamp}.sql"

    with tempfile.TemporaryDirectory() as tmp:
        dump_path = os.path.join(tmp, filename)

        env = os.environ.copy()
        env["PGPASSWORD"] = db["password"]

        result = subprocess.run(
            [
                "pg_dump",
                "-h", db["host"],
                "-p", db["port"],
                "-U", db["user"],
                "-d", db["dbname"],
                "-f", dump_path,
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

        file_size = os.path.getsize(dump_path)

        # Upload to S3
        client = _get_s3_client()
        s3_key = f"backups/{filename}"
        try:
            client.upload_file(
                dump_path,
                bucket,
                s3_key,
                ExtraArgs={"ContentType": "application/sql"},
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to upload to S3: {e}")

    logger.info(f"Backup uploaded: s3://{bucket}/{s3_key} ({file_size} bytes)")
    return {
        "filename": filename,
        "s3_key": s3_key,
        "bucket": bucket,
        "size_bytes": file_size,
        "timestamp": timestamp,
    }


def list_backups() -> list[dict]:
    """List existing backups in the S3 bucket."""
    bucket = os.environ.get("AWS_S3_BUCKET", "agent-games-backups")
    client = _get_s3_client()

    try:
        response = client.list_objects_v2(Bucket=bucket, Prefix="backups/")
    except ClientError as e:
        raise RuntimeError(f"Failed to list backups: {e}")

    backups = []
    for obj in response.get("Contents", []):
        backups.append({
            "filename": obj["Key"].split("/")[-1],
            "s3_key": obj["Key"],
            "size_bytes": obj["Size"],
            "last_modified": obj["LastModified"].isoformat(),
        })

    # Most recent first
    backups.sort(key=lambda b: b["last_modified"], reverse=True)
    return backups


def restore_backup(s3_key: str) -> dict:
    """Download a backup from S3 and restore it via psql.

    This drops and recreates the database before restoring.
    """
    bucket = os.environ.get("AWS_S3_BUCKET", "agent-games-backups")
    db = _parse_db_url()
    client = _get_s3_client()

    with tempfile.TemporaryDirectory() as tmp:
        filename = s3_key.split("/")[-1]
        dump_path = os.path.join(tmp, filename)

        # Download from S3
        try:
            client.download_file(bucket, s3_key, dump_path)
        except ClientError as e:
            raise RuntimeError(f"Failed to download backup from S3: {e}")

        env = os.environ.copy()
        env["PGPASSWORD"] = db["password"]
        psql_base = ["psql", "-h", db["host"], "-p", db["port"], "-U", db["user"]]

        # Terminate existing connections to the target database
        result = subprocess.run(
            psql_base + ["-d", "postgres", "-c",
                         f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                         f"WHERE datname = '{db['dbname']}' AND pid <> pg_backend_pid();"],
            capture_output=True, text=True, env=env, timeout=30,
        )

        # Drop and recreate the database
        result = subprocess.run(
            psql_base + ["-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {db['dbname']};"],
            capture_output=True, text=True, env=env, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"DROP DATABASE failed: {result.stderr}")

        result = subprocess.run(
            psql_base + ["-d", "postgres", "-c", f"CREATE DATABASE {db['dbname']};"],
            capture_output=True, text=True, env=env, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"CREATE DATABASE failed: {result.stderr}")

        # Restore the dump
        result = subprocess.run(
            psql_base + ["-d", db["dbname"], "-f", dump_path],
            capture_output=True, text=True, env=env, timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"psql restore failed: {result.stderr}")

    logger.info(f"Database restored from s3://{bucket}/{s3_key}")
    return {"filename": filename, "s3_key": s3_key}
