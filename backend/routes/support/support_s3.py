import logging
import os
from uuid import uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_support_bucket() -> str:
    return os.environ.get("AWS_S3_SUPPORT_BUCKET", "agent-games-support-attachments")


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


def _get_presign_client():
    """
    Presign client. In dev S3_ENDPOINT_URL points at `minio:9000` (docker DNS),
    which is unreachable from a browser on the host. S3_PUBLIC_ENDPOINT_URL
    overrides the host used when generating presigned URLs so admins can load
    images. In AWS prod, both are unset and boto3 uses the default endpoint.
    """
    public = os.environ.get("S3_PUBLIC_ENDPOINT_URL") or os.environ.get(
        "S3_ENDPOINT_URL"
    )
    return _build_client(public)


def upload_attachment(
    file_bytes: bytes, content_type: str, ticket_id: int, idx: int
) -> str:
    """Upload one image to the support bucket and return its S3 key."""
    s3_key = f"tickets/{ticket_id}/{uuid4().hex}_{idx}"
    _get_s3_client().put_object(
        Bucket=get_support_bucket(),
        Key=s3_key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return s3_key


def delete_attachment(s3_key: str) -> None:
    """Best-effort delete — swallows errors for rollback scenarios."""
    try:
        _get_s3_client().delete_object(Bucket=get_support_bucket(), Key=s3_key)
    except ClientError as exc:
        logger.warning(f"Failed to delete s3 object {s3_key}: {exc}")


def presign_attachment(s3_key: str, expires: int = 900) -> str:
    """Generate a short-lived presigned GET URL for the admin view."""
    return _get_presign_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": get_support_bucket(), "Key": s3_key},
        ExpiresIn=expires,
    )
