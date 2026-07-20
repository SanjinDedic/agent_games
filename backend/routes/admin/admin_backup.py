import logging
import os
import subprocess
import tempfile
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import boto3
from botocore.exceptions import ClientError

from backend.database.db_config import get_database_url
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)


def _parse_db_url():
    """Extract host, port, user, password, dbname, sslmode from the SQLAlchemy DATABASE_URL."""
    raw = get_database_url()
    # Strip the +psycopg driver so urlparse handles it cleanly
    raw = raw.replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(raw)
    query = parse_qs(parsed.query)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/"),
        # Production is a TLS-only managed cluster. pg_dump/pg_restore/psql take
        # the connection as flags rather than a URL, so the sslmode carried in
        # DATABASE_URL's query string has to be re-injected via PGSSLMODE.
        "sslmode": query.get("sslmode", ["prefer"])[0],
    }


def _pg_env(db: dict) -> dict:
    """Environment for the libpq CLIs: password + TLS mode out of the URL."""
    env = os.environ.copy()
    env["PGPASSWORD"] = db["password"]
    env["PGSSLMODE"] = db["sslmode"]
    return env


# Reset `public` to empty so a restore has somewhere clean to land, using only
# rights the app role actually has on the managed cluster.
#
# It cannot DROP SCHEMA public (owned by pg_database_owner, i.e. doadmin), and
# DROP OWNED BY CURRENT_USER — the obvious shortcut — would also revoke this
# role's own USAGE/CREATE grants on public, leaving the next create_all locked
# out. So drop the objects one kind at a time: tables (CASCADE takes their
# constraints, indexes and identity sequences), then any standalone sequences,
# then the native enum types SQLModel emits for the str-Enum fields — without
# that last step pg_restore fails with "type ... already exists".
_WIPE_PUBLIC_SCHEMA_SQL = """
DO $$
DECLARE obj record;
BEGIN
    FOR obj IN
        SELECT c.relname AS name FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', obj.name);
    END LOOP;

    FOR obj IN
        SELECT c.relname AS name FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'S'
    LOOP
        EXECUTE format('DROP SEQUENCE IF EXISTS public.%I CASCADE', obj.name);
    END LOOP;

    FOR obj IN
        SELECT t.typname AS name FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public' AND t.typtype = 'e'
    LOOP
        EXECUTE format('DROP TYPE IF EXISTS public.%I CASCADE', obj.name);
    END LOOP;
END $$;
"""


def _get_s3_client():
    """Build a boto3 S3 client for AWS.

    Honours S3_ENDPOINT_URL like the assets/support clients do (support_s3.py),
    so in dev the client targets MinIO (http://minio:9000) instead of real AWS.
    When unset (production on real AWS S3) it falls back to the default endpoint.
    """
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
        endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
    )


def create_backup(label: str = "MANUAL") -> dict:
    """Run pg_dump (custom format, zstd-compressed) and upload the .dump to AWS S3.

    `label` tags the filename with the backup's origin (MANUAL, DAILY, PRE_DEPLOY).
    Returns a dict with backup metadata on success.
    """
    bucket = os.environ.get("AWS_S3_BUCKET", "agent-games-backups")
    db = _parse_db_url()
    timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
    filename = f"agent_games_{label}_{timestamp}.dump"

    with tempfile.TemporaryDirectory() as tmp:
        dump_path = os.path.join(tmp, filename)

        env = _pg_env(db)

        result = subprocess.run(
            [
                "pg_dump",
                "-h", db["host"],
                "-p", db["port"],
                "-U", db["user"],
                "-d", db["dbname"],
                "--format=custom",
                "--compress=zstd:3",
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
                ExtraArgs={"ContentType": "application/octet-stream"},
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


def prune_backups(days: int = 60) -> list[str]:
    """Delete backups older than `days` days from the S3 bucket.

    Only touches keys matching backups/agent_games_*. Returns the deleted keys.
    """
    bucket = os.environ.get("AWS_S3_BUCKET", "agent-games-backups")
    client = _get_s3_client()
    cutoff = utc_now() - timedelta(days=days)

    try:
        response = client.list_objects_v2(Bucket=bucket, Prefix="backups/")
    except ClientError as e:
        raise RuntimeError(f"Failed to list backups: {e}")

    expired = [
        obj["Key"]
        for obj in response.get("Contents", [])
        if obj["Key"].startswith("backups/agent_games_")
        and obj["LastModified"] < cutoff
    ]
    if not expired:
        return []

    try:
        client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in expired], "Quiet": True},
        )
    except ClientError as e:
        raise RuntimeError(f"Failed to delete old backups: {e}")

    logger.info(f"Pruned {len(expired)} backup(s) older than {days} days")
    return expired


def restore_backup(s3_key: str) -> dict:
    """Download a backup from S3 and restore it.

    Custom-format archives (.dump) restore via pg_restore; legacy plain-SQL
    backups (.sql) still restore via psql. Either way the `public` schema is
    emptied first so the restore lands in a clean database.
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

        env = _pg_env(db)
        psql_base = ["psql", "-h", db["host"], "-p", db["port"], "-U", db["user"]]

        # Empty the database in place (see _WIPE_PUBLIC_SCHEMA_SQL) instead of
        # DROP/CREATE DATABASE, which the app role cannot do on the managed
        # cluster: doadmin owns the database, and there is no `postgres`
        # maintenance database for the app role to connect to.
        result = subprocess.run(
            psql_base + ["-d", db["dbname"], "-v", "ON_ERROR_STOP=1",
                         "-c", _WIPE_PUBLIC_SCHEMA_SQL],
            capture_output=True, text=True, env=env, timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Wiping the public schema failed: {result.stderr}")

        # Restore the dump. Legacy backups are plain SQL; current ones are
        # pg_dump custom-format archives.
        if filename.endswith(".sql"):
            restore_cmd = psql_base + ["-d", db["dbname"], "-f", dump_path]
        else:
            restore_cmd = [
                "pg_restore",
                "-h", db["host"],
                "-p", db["port"],
                "-U", db["user"],
                "-d", db["dbname"],
                "--no-owner",
                dump_path,
            ]
        result = subprocess.run(
            restore_cmd,
            capture_output=True, text=True, env=env, timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"restore failed: {result.stderr}")

    logger.info(f"Database restored from s3://{bucket}/{s3_key}")
    return {"filename": filename, "s3_key": s3_key}


if __name__ == "__main__":
    # CLI entry for scheduled/pre-deploy backups, run inside the api container:
    #   python -m backend.routes.admin.admin_backup --label DAILY --prune
    import argparse

    parser = argparse.ArgumentParser(description="Back up the database to S3")
    parser.add_argument(
        "--label",
        default="MANUAL",
        help="Origin tag embedded in the backup filename (e.g. DAILY, PRE_DEPLOY)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="After backing up, delete backups older than 60 days",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    result = create_backup(label=args.label)
    print(f"Backup created: s3://{result['bucket']}/{result['s3_key']} "
          f"({result['size_bytes']} bytes)")
    if args.prune:
        deleted = prune_backups()
        print(f"Pruned {len(deleted)} backup(s) older than 60 days")
