"""Sync site image files from a local directory into the assets bucket.

A maintainer script, not part of the running app: the frontend loads these images
straight from VITE_ASSETS_URL, so nothing in the stack needs object storage at
runtime. Run it from a workstation with AWS credentials — the containers carry
none, and there is no local MinIO to point at any more. Content-type is inferred
from the extension.

Usage:
    AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... \\
        python -m backend.scripts.sync_site_images

Override source / prefix with SYNC_SOURCE_DIR and SYNC_DEST_PREFIX.
"""

import logging
import mimetypes
import os
from pathlib import Path

from backend.s3 import _get_s3_client, get_assets_bucket

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
