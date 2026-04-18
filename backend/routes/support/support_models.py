from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from backend.database.db_models import (
    SupportTicketCategory,
    SupportTicketStatus,
    SupportTicketSubmitterType,
)

MAX_SUBJECT_LEN = 200
MAX_DESCRIPTION_LEN = 5000
MAX_ATTACHMENTS = 3
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


class SupportTicketAttachmentOut(BaseModel):
    id: int
    url: str
    content_type: str
    size_bytes: int
    original_filename: str


class SupportTicketSubmitterOut(BaseModel):
    id: int
    name: str
    institution_name: Optional[str] = None
    contact_email: Optional[str] = None


class SupportTicketOut(BaseModel):
    id: int
    category: SupportTicketCategory
    subject: str
    description: str
    status: SupportTicketStatus
    admin_note: Optional[str] = None
    submitter_type: SupportTicketSubmitterType
    submitter: Optional[SupportTicketSubmitterOut] = None
    attachments: List[SupportTicketAttachmentOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UpdateSupportTicketRequest(BaseModel):
    ticket_id: int
    status: Optional[SupportTicketStatus] = None
    admin_note: Optional[str] = None
