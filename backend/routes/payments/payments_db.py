"""Database helpers for payment-gated institution signup.

Mirrors backend.routes.admin.admin_db.create_institution (admin-created
institutions) but is driven by a verified Stripe Checkout Session: the caller
must have confirmed payment before invoking create_paid_institution.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    InstitutionSubscription,
    League,
    LeagueType,
    get_password_hash,
)
from backend.time_utils import utc_now

logger = logging.getLogger(__name__)


class PaidSignupError(Exception):
    """Raised when a payment-gated institution signup cannot be completed (400)."""


class InstitutionExistsError(PaidSignupError):
    """Raised when the requested institution name is already taken (409)."""


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
    tier: Optional[str] = None,
    is_teacher: bool = False,
) -> Institution:
    """Create an institution after its Stripe payment has been verified.

    Idempotency/replay is enforced on stripe_checkout_session_id (unique on the
    subscription record): if a subscription already exists for this session, the
    existing institution is returned instead of creating a duplicate or charging
    the buyer twice in effect.
    """
    # A given paid session creates exactly one institution. If the buyer
    # double-submits the form (or refreshes), return what already exists.
    existing_for_session = session.exec(
        select(InstitutionSubscription).where(
            InstitutionSubscription.stripe_checkout_session_id
            == stripe_checkout_session_id
        )
    ).first()
    if existing_for_session:
        return existing_for_session.institution

    name = name.strip()
    if not name:
        raise PaidSignupError("Institution name cannot be empty")

    existing_name = session.exec(
        select(Institution).where(Institution.name == name)
    ).first()
    if existing_name:
        raise InstitutionExistsError(f"Institution with name '{name}' already exists")

    now = utc_now()
    institution = Institution(
        name=name,
        contact_person=contact_person,
        contact_email=contact_email,
        address=address,
        created_date=now,
        is_teacher=is_teacher,
    )
    institution.set_password(password)

    session.add(institution)
    session.flush()  # Assign institution.id before creating dependent rows

    session.add(
        InstitutionSubscription(
            institution_id=institution.id,
            payment_method="card",
            tier=tier,
            subscription_active=True,
            subscription_expiry=subscription_expiry,
            auto_renew=auto_renew,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_checkout_session_id=stripe_checkout_session_id,
            created_date=now,
        )
    )

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
    tier: Optional[str] = None,
) -> Institution:
    """Create an institution plus its InstitutionSubscription billing record for
    an invoiced annual subscription.

    Access is granted immediately: the Stripe invoice has been issued and
    payment follows on net terms. The teaching contact becomes the institution's
    login/primary contact; the business contact is retained on the subscription
    record for billing only.
    """
    institution_name = institution_name.strip()
    if not institution_name:
        raise PaidSignupError("Institution name cannot be empty")

    existing_name = session.exec(
        select(Institution).where(Institution.name == institution_name)
    ).first()
    if existing_name:
        raise InstitutionExistsError(
            f"Institution with name '{institution_name}' already exists"
        )

    now = utc_now()
    institution = Institution(
        name=institution_name,
        contact_person=teaching_contact_name,
        contact_email=teaching_contact_email,
        address=institution_address,
        created_date=now,
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

    # Subscription + billing record. The business contact (who pays the invoice)
    # is kept here, distinct from the institution's teaching/login contact above.
    session.add(
        InstitutionSubscription(
            institution_id=institution.id,
            payment_method="invoice",
            tier=tier,
            subscription_active=True,
            subscription_expiry=subscription_expiry,
            auto_renew=True,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_invoice_id=stripe_invoice_id,
            business_contact_name=business_contact_name,
            business_contact_email=business_contact_email,
            created_date=now,
        )
    )

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
