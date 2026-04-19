"""Sync site image files from a local directory into the assets bucket.

Works against MinIO locally and real S3 in prod — whichever endpoint the
AWS_* env vars already point at. Content-type is inferred from the extension.

Usage (inside the api container, dev):
    docker compose exec api python -m backend.scripts.sync_site_images

Override source / prefix:
    docker compose exec -e SYNC_SOURCE_DIR=/agent_games/frontend/public/games \\
        -e SYNC_DEST_PREFIX=images/games \\
        api python -m backend.scripts.sync_site_images

Run against AWS (from a workstation with AWS creds, no docker needed):
    AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... \\
        python -m backend.scripts.sync_site_images
"""

import logging
import mimetypes
import os
from pathlib import Path

from backend.routes.support.support_s3 import _get_s3_client, get_assets_bucket

logger = logging.getLogger(__name__)

DEFAULT_SOURCE = "/agent_games/frontend/public/games"
DEFAULT_PREFIX = "images/games"


def sync() -> dict:
    source = Path(os.environ.get("SYNC_SOURCE_DIR", DEFAULT_SOURCE))
    prefix = os.environ.get("SYNC_DEST_PREFIX", DEFAULT_PREFIX).strip("/")
    bucket = get_assets_bucket()
    client = _get_s3_client()

    if not source.is_dir():
        raise RuntimeError(f"Source dir not found: {source}")

    uploaded = 0
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source).as_posix()
        key = f"{prefix}/{rel}" if prefix else rel
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as f:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=f.read(),
                ContentType=content_type,
            )
        logger.info(f"uploaded {rel} → s3://{bucket}/{key} ({content_type})")
        uploaded += 1

    return {"bucket": bucket, "prefix": prefix, "source": str(source), "uploaded": uploaded}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = sync()
    logger.info(f"Sync complete: {result}")
    print(result)
