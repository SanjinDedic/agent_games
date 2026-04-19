"""One-shot migration: move support attachments from the legacy bucket
(agent-games-support-attachments) into the consolidated `assets` bucket
under `support/{institution|user}/{ticket_id}/...`.

Idempotent — rows whose s3_key already starts with `support/` are skipped.

Usage (inside the api container):
    docker compose exec api python -m backend.scripts.migrate_support_to_assets

Override the source bucket if needed:
    MIGRATE_SOURCE_BUCKET=<name> docker compose exec -e MIGRATE_SOURCE_BUCKET api \\
        python -m backend.scripts.migrate_support_to_assets
"""

import logging
import os
from posixpath import basename

from botocore.exceptions import ClientError
from sqlmodel import Session, select

from backend.database.db_models import (
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketSubmitterType,
)
from backend.database.db_session import get_db_engine
from backend.routes.support.support_s3 import (
    _get_s3_client,
    _submitter_folder,
    get_assets_bucket,
)

logger = logging.getLogger(__name__)


def _source_bucket() -> str:
    return os.environ.get("MIGRATE_SOURCE_BUCKET", "agent-games-support-attachments")


def migrate() -> dict:
    source = _source_bucket()
    dest = get_assets_bucket()
    client = _get_s3_client()

    migrated = 0
    skipped = 0
    missing = 0

    with Session(get_db_engine()) as session:
        rows = session.exec(
            select(SupportTicketAttachment, SupportTicket).where(
                SupportTicketAttachment.ticket_id == SupportTicket.id
            )
        ).all()

        for attachment, ticket in rows:
            if attachment.s3_key.startswith("support/"):
                skipped += 1
                continue

            folder = _submitter_folder(
                ticket.submitter_type or SupportTicketSubmitterType.TEAM
            )
            new_key = f"support/{folder}/{ticket.id}/{basename(attachment.s3_key)}"

            try:
                client.copy_object(
                    Bucket=dest,
                    Key=new_key,
                    CopySource={"Bucket": source, "Key": attachment.s3_key},
                )
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in ("NoSuchKey", "404"):
                    logger.warning(
                        f"Source object missing, rewriting DB key anyway: "
                        f"{source}/{attachment.s3_key} → {dest}/{new_key}"
                    )
                    missing += 1
                    attachment.s3_key = new_key
                    session.add(attachment)
                    session.commit()
                    continue
                raise

            try:
                client.delete_object(Bucket=source, Key=attachment.s3_key)
            except ClientError as exc:
                logger.warning(
                    f"Copied but could not delete source "
                    f"{source}/{attachment.s3_key}: {exc}"
                )

            attachment.s3_key = new_key
            session.add(attachment)
            session.commit()
            migrated += 1

    return {"migrated": migrated, "skipped": skipped, "missing_source": missing}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = migrate()
    logger.info(f"Migration complete: {result}")
    print(result)
