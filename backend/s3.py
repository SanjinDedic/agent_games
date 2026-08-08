"""S3 client construction.

Used only by backend/scripts/sync_site_images.py, a maintainer script — no part
of the running app talks to object storage. S3_ENDPOINT_URL still overrides the
endpoint if you point it at something, but nothing sets it now that the local
MinIO service is gone; unset, boto3 resolves the real AWS endpoint.
"""

import os

import boto3
from botocore.client import Config


def get_assets_bucket() -> str:
    return os.environ.get("AWS_S3_ASSETS_BUCKET", "assets")


def _build_client(endpoint: str | None):
    key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    region = os.environ.get("AWS_REGION", "ap-southeast-2")
    if not all([key, secret]):
        raise RuntimeError(
            "Missing AWS credentials. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
        )
    return boto3.client(
        "s3",
        aws_access_key_id=key,
        aws_secret_access_key=secret,
        region_name=region,
        endpoint_url=endpoint or None,
        config=Config(signature_version="s3v4"),
    )


def _get_s3_client():
    """Server-side client — talks to MinIO over the docker network or real AWS."""
    return _build_client(os.environ.get("S3_ENDPOINT_URL"))
