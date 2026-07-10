import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session

from backend.database.db_session import get_db
from backend.routes.auth.auth_core import (
    ROLE_INSTITUTION,
    ROLE_STUDENT,
    get_current_user,
    verify_non_admin,
)
from backend.routes.support.support_db import add_attachment, create_ticket
from backend.database.db_models import (
    SupportTicketCategory,
    SupportTicketSubmitterType,
)
from backend.routes.support.support_models import (
    ALLOWED_CONTENT_TYPES,
    MAX_ATTACHMENT_BYTES,
    MAX_ATTACHMENTS,
    MAX_DESCRIPTION_LEN,
    MAX_SUBJECT_LEN,
)
from backend.routes.support.support_s3 import delete_attachment, upload_attachment

logger = logging.getLogger(__name__)

support_router = APIRouter()


@support_router.post("/create-ticket")
@verify_non_admin
async def create_ticket_endpoint(
    category: str = Form(...),
    subject: str = Form(...),
    description: str = Form(...),
    files: Optional[List[UploadFile]] = File(default=None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Submit a support ticket. Available to team (student) and institution users."""
    try:
        category_enum = SupportTicketCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")

    subject = (subject or "").strip()
    description = (description or "").strip()
    if not subject or len(subject) > MAX_SUBJECT_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Subject must be 1-{MAX_SUBJECT_LEN} characters",
        )
    if not description or len(description) > MAX_DESCRIPTION_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Description must be 1-{MAX_DESCRIPTION_LEN} characters",
        )

    files = files or []
    if len(files) > MAX_ATTACHMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"At most {MAX_ATTACHMENTS} attachments allowed",
        )

    file_payloads = []
    for upload in files:
        content = await upload.read()
        if len(content) > MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Attachment '{upload.filename}' exceeds 5 MB",
            )
        if (upload.content_type or "").lower() not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Attachment '{upload.filename}' must be PNG, JPEG, or WebP",
            )
        if not content:
            raise HTTPException(
                status_code=400,
                detail=f"Attachment '{upload.filename}' is empty",
            )
        file_payloads.append(
            {
                "bytes": content,
                "content_type": upload.content_type.lower(),
                "filename": upload.filename or "upload",
            }
        )

    role = current_user["role"]
    if role == ROLE_STUDENT:
        submitter_type = SupportTicketSubmitterType.TEAM
        team_id, institution_id = current_user.get("team_id"), None
        if team_id is None:
            raise HTTPException(status_code=401, detail="Token missing team_id")
    elif role == ROLE_INSTITUTION:
        submitter_type = SupportTicketSubmitterType.INSTITUTION
        team_id, institution_id = None, current_user.get("institution_id")
        if institution_id is None:
            raise HTTPException(
                status_code=401, detail="Token missing institution_id"
            )
    else:
        raise HTTPException(
            status_code=403,
            detail="Only team and institution users can submit support tickets",
        )

    ticket = create_ticket(
        session,
        category=category_enum,
        subject=subject,
        description=description,
        submitter_type=submitter_type,
        team_id=team_id,
        institution_id=institution_id,
    )

    uploaded_keys: List[str] = []
    try:
        for idx, payload in enumerate(file_payloads):
            s3_key = upload_attachment(
                payload["bytes"],
                payload["content_type"],
                ticket.id,
                idx,
                submitter_type,
            )
            uploaded_keys.append(s3_key)
            add_attachment(
                session,
                ticket_id=ticket.id,
                s3_key=s3_key,
                content_type=payload["content_type"],
                size_bytes=len(payload["bytes"]),
                original_filename=payload["filename"],
            )
        session.commit()
    except Exception as exc:
        # Compensating cleanup, not error masking: roll back the ticket and
        # best-effort delete any S3 objects already uploaded, then surface a 500.
        session.rollback()
        for key in uploaded_keys:
            delete_attachment(key)
        logger.error(f"Failed to store attachments: {exc}")
        raise HTTPException(status_code=500, detail="Failed to store attachments")

    return {"ticket_id": ticket.id, "attachments": len(uploaded_keys)}
