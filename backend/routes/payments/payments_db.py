"""Database helpers for payment-gated institution signup.

Mirrors backend.routes.admin.admin_db.create_institution (admin-created
institutions) but is driven by a verified Stripe Checkout Session: the caller
must have confirmed payment before invoking create_paid_institution.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pytz
from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    League,
    LeagueType,
    PaymentClient,
    get_password_hash,
)

logger = logging.getLogger(__name__)
AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


class PaidSignupError(Exception):
    """Raised when a payment-gated institution signup cannot be completed."""

    pass


def create_paid_institution(
    session: Session,
    *,
    name: str,
    contact_person: str,
    contact_email: str,
    address: Optional[str],
    password: str,
    subscription_expiry: datetime,
    auto_renew: bool,
    stripe_customer_id: Optional[str],
    stripe_subscription_id: Optional[str],
    stripe_checkout_session_id: str,
) -> Institution:
    """Create an institution after its Stripe payment has been verified.

    Idempotency/replay is enforced on stripe_checkout_session_id: if a row
    already exists for this session, the existing institution is returned
    instead of creating a duplicate or charging the buyer twice in effect.
    """
    # A given paid session creates exactly one institution. If the buyer
    # double-submits the form (or refreshes), return what already exists.
    existing_for_session = session.exec(
        select(Institution).where(
            Institution.stripe_checkout_session_id == stripe_checkout_session_id
        )
    ).first()
    if existing_for_session:
        return existing_for_session

    name = name.strip()
    if not name:
        raise PaidSignupError("Institution name cannot be empty")

    existing_name = session.exec(
        select(Institution).where(Institution.name == name)
    ).first()
    if existing_name:
        raise PaidSignupError(f"Institution with name '{name}' already exists")

    now = datetime.now(AUSTRALIA_SYDNEY_TZ)
    institution = Institution(
        name=name,
        contact_person=contact_person,
        contact_email=contact_email,
        address=address,
        created_date=now,
        subscription_active=True,
        subscription_expiry=subscription_expiry,
        auto_renew=auto_renew,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        stripe_checkout_session_id=stripe_checkout_session_id,
        docker_access=False,
    )
    institution.set_password(password)

    session.add(institution)
    session.flush()  # Assign institution.id before creating its league

    # Every institution gets an "unassigned" league (matches admin-created flow).
    unassigned_league = League(
        name="unassigned",
        created_date=now,
        expiry_date=now + timedelta(days=365),
        game="greedy_pig",
        league_type=LeagueType.INSTITUTION,
        institution_id=institution.id,
    )
    session.add(unassigned_league)

    session.commit()
    session.refresh(institution)
    logger.info(
        "Paid institution created: id=%s name=%s session=%s",
        institution.id,
        name,
        stripe_checkout_session_id,
    )
    return institution


def create_invoiced_institution(
    session: Session,
    *,
    institution_name: str,
    institution_address: str,
    business_contact_name: str,
    business_contact_email: str,
    teaching_contact_name: str,
    teaching_contact_email: str,
    password: str,
    subscription_expiry: datetime,
    stripe_customer_id: Optional[str],
    stripe_subscription_id: Optional[str],
    stripe_invoice_id: Optional[str],
) -> Institution:
    """Create an institution plus its PaymentClient billing record for an
    invoiced annual subscription.

    Access is granted immediately: the Stripe invoice has been issued and
    payment follows on net terms. The teaching contact becomes the institution's
    login/primary contact; the business contact is retained on the PaymentClient
    for billing only.
    """
    institution_name = institution_name.strip()
    if not institution_name:
        raise PaidSignupError("Institution name cannot be empty")

    existing_name = session.exec(
        select(Institution).where(Institution.name == institution_name)
    ).first()
    if existing_name:
        raise PaidSignupError(
            f"Institution with name '{institution_name}' already exists"
        )

    now = datetime.now(AUSTRALIA_SYDNEY_TZ)
    institution = Institution(
        name=institution_name,
        contact_person=teaching_contact_name,
        contact_email=teaching_contact_email,
        address=institution_address,
        created_date=now,
        subscription_active=True,
        subscription_expiry=subscription_expiry,
        auto_renew=True,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        stripe_checkout_session_id=None,
        docker_access=False,
    )
    institution.set_password(password)

    session.add(institution)
    session.flush()  # Assign institution.id before creating dependent rows

    # Every institution gets an "unassigned" league (matches the other flows).
    unassigned_league = League(
        name="unassigned",
        created_date=now,
        expiry_date=now + timedelta(days=365),
        game="greedy_pig",
        league_type=LeagueType.INSTITUTION,
        institution_id=institution.id,
    )
    session.add(unassigned_league)

    payment_client = PaymentClient(
        institution_id=institution.id,
        institution_name=institution_name,
        institution_address=institution_address,
        business_contact_name=business_contact_name,
        business_contact_email=business_contact_email,
        teaching_contact_name=teaching_contact_name,
        teaching_contact_email=teaching_contact_email,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        stripe_invoice_id=stripe_invoice_id,
        created_date=now,
    )
    session.add(payment_client)

    session.commit()
    session.refresh(institution)
    logger.info(
        "Invoiced institution created: id=%s name=%s subscription=%s invoice=%s",
        institution.id,
        institution_name,
        stripe_subscription_id,
        stripe_invoice_id,
    )
    return institution
