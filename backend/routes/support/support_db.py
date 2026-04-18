import logging
from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketCategory,
    SupportTicketStatus,
    SupportTicketSubmitterType,
    Team,
)
from backend.routes.support.support_models import (
    SupportTicketAttachmentOut,
    SupportTicketOut,
    SupportTicketSubmitterOut,
)
from backend.routes.support.support_s3 import delete_attachment, presign_attachment

logger = logging.getLogger(__name__)


class SupportError(Exception):
    """Raised for support-ticket validation or lookup failures."""


def resolve_team_by_token_name(session: Session, team_name: str) -> Team:
    team = session.exec(select(Team).where(Team.name == team_name)).first()
    if not team:
        raise SupportError(f"Team '{team_name}' not found")
    return team


def resolve_institution_by_token_name(session: Session, institution_name: str) -> Institution:
    institution = session.exec(
        select(Institution).where(Institution.name == institution_name)
    ).first()
    if not institution:
        raise SupportError(f"Institution '{institution_name}' not found")
    return institution


def create_ticket(
    session: Session,
    *,
    category: SupportTicketCategory,
    subject: str,
    description: str,
    submitter_type: SupportTicketSubmitterType,
    team_id: Optional[int],
    institution_id: Optional[int],
) -> SupportTicket:
    now = datetime.utcnow()
    ticket = SupportTicket(
        category=category,
        subject=subject,
        description=description,
        status=SupportTicketStatus.OPEN,
        submitter_type=submitter_type,
        team_id=team_id,
        institution_id=institution_id,
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    session.flush()
    return ticket


def add_attachment(
    session: Session,
    *,
    ticket_id: int,
    s3_key: str,
    content_type: str,
    size_bytes: int,
    original_filename: str,
) -> SupportTicketAttachment:
    att = SupportTicketAttachment(
        ticket_id=ticket_id,
        s3_key=s3_key,
        content_type=content_type,
        size_bytes=size_bytes,
        original_filename=original_filename,
    )
    session.add(att)
    session.flush()
    return att


def list_tickets(
    session: Session,
    *,
    submitter_type: Optional[SupportTicketSubmitterType] = None,
    status: Optional[SupportTicketStatus] = None,
) -> List[SupportTicketOut]:
    stmt = select(SupportTicket).order_by(SupportTicket.created_at.desc())
    if submitter_type is not None:
        stmt = stmt.where(SupportTicket.submitter_type == submitter_type)
    if status is not None:
        stmt = stmt.where(SupportTicket.status == status)

    tickets = session.exec(stmt).all()
    return [_ticket_to_out(session, t) for t in tickets]


def delete_ticket(session: Session, ticket_id: int) -> dict:
    """Delete a ticket, its attachment rows, and best-effort remove S3 objects."""
    ticket = session.get(SupportTicket, ticket_id)
    if not ticket:
        raise SupportError(f"Ticket {ticket_id} not found")

    s3_keys = [att.s3_key for att in ticket.attachments]
    attachment_count = len(s3_keys)

    session.delete(ticket)
    session.commit()

    for key in s3_keys:
        delete_attachment(key)

    return {"ticket_id": ticket_id, "attachments_deleted": attachment_count}


def update_ticket(
    session: Session,
    *,
    ticket_id: int,
    status: Optional[SupportTicketStatus] = None,
    admin_note: Optional[str] = None,
) -> SupportTicketOut:
    ticket = session.get(SupportTicket, ticket_id)
    if not ticket:
        raise SupportError(f"Ticket {ticket_id} not found")

    if status is not None:
        ticket.status = status
    if admin_note is not None:
        ticket.admin_note = admin_note
    ticket.updated_at = datetime.utcnow()

    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return _ticket_to_out(session, ticket)


def _ticket_to_out(session: Session, ticket: SupportTicket) -> SupportTicketOut:
    submitter: Optional[SupportTicketSubmitterOut] = None
    if ticket.submitter_type == SupportTicketSubmitterType.TEAM and ticket.team_id:
        team = session.get(Team, ticket.team_id)
        if team:
            institution_name = team.institution.name if team.institution else team.school_name
            submitter = SupportTicketSubmitterOut(
                id=team.id,
                name=team.name,
                institution_name=institution_name,
            )
    elif (
        ticket.submitter_type == SupportTicketSubmitterType.INSTITUTION
        and ticket.institution_id
    ):
        inst = session.get(Institution, ticket.institution_id)
        if inst:
            submitter = SupportTicketSubmitterOut(
                id=inst.id,
                name=inst.name,
                contact_email=inst.contact_email,
            )

    attachments_out: List[SupportTicketAttachmentOut] = []
    for att in ticket.attachments:
        try:
            url = presign_attachment(att.s3_key)
        except Exception as exc:
            logger.warning(f"Could not presign {att.s3_key}: {exc}")
            url = ""
        attachments_out.append(
            SupportTicketAttachmentOut(
                id=att.id,
                url=url,
                content_type=att.content_type,
                size_bytes=att.size_bytes,
                original_filename=att.original_filename,
            )
        )

    return SupportTicketOut(
        id=ticket.id,
        category=ticket.category,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        admin_note=ticket.admin_note,
        submitter_type=ticket.submitter_type,
        submitter=submitter,
        attachments=attachments_out,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )
