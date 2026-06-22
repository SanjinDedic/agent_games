import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from backend import config
from backend.database.db_models import Institution, InstitutionSubscription
from backend.database.db_session import get_db
from backend.models_api import ResponseModel
from backend.routes.payments.payments_db import (
    PaidSignupError,
    create_invoiced_institution,
    create_paid_institution,
)

logger = logging.getLogger(__name__)

payments_router = APIRouter()

stripe.api_key = config.STRIPE_SECRET_KEY

# (tier, auto_renew) -> Stripe Price ID. The one-time Prices are the cheaper
# 90-day passes (Checkout mode="payment"); the yearly recurring Prices are the
# annual auto-renewing subscriptions (mode="subscription"). The two Prices in a
# tier are NOT the same amount: the annual plan costs more than a 90-day pass.
_TIER_PRICES = {
    ("club", False): config.STRIPE_PRICE_CLUB_ONCE,
    ("club", True): config.STRIPE_PRICE_CLUB_YEAR,
    ("university", False): config.STRIPE_PRICE_UNI_ONCE,
    ("university", True): config.STRIPE_PRICE_UNI_YEAR,
}

# One-time purchases buy a fixed 90-day access window.
ONE_OFF_DAYS = 90

# Net terms for the invoiced annual plan: the issued invoice is due in 30 days.
INVOICE_DUE_DAYS = 30


class CheckoutRequest(BaseModel):
    tier: str
    auto_renew: bool = False


class InvoiceSignupRequest(BaseModel):
    tier: str
    institution_name: str
    institution_address: str
    business_contact_name: str
    business_contact_email: str
    teaching_contact_name: str
    teaching_contact_email: str
    password: str


class InstitutionSignupRequest(BaseModel):
    session_id: str
    name: str
    contact_person: str
    address: Optional[str] = None
    password: str
    # NOTE: the buyer's email is read from the verified Stripe session
    # server-side, never accepted from the client (the grayed field is UI only).


def _price_for(tier: str, auto_renew: bool) -> str:
    price_id = _TIER_PRICES.get((tier, auto_renew))
    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown or unconfigured tier: {tier!r}",
        )
    return price_id


def _require_stripe() -> None:
    if not config.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe is not configured")


def _utc_from_ts(ts: Optional[int]) -> Optional[datetime]:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _subscription_period_end(sub: dict) -> Optional[datetime]:
    """Read the current period end from a Subscription across API versions.

    Newer API versions expose current_period_end on subscription items rather
    than the subscription itself; fall back to the top-level field.
    """
    items = (sub.get("items") or {}).get("data") or []
    if items and items[0].get("current_period_end"):
        return _utc_from_ts(items[0]["current_period_end"])
    return _utc_from_ts(sub.get("current_period_end"))


def _format_address(details: Optional[dict]) -> Optional[str]:
    addr = (details or {}).get("address") or {}
    parts = [
        addr.get("line1"),
        addr.get("line2"),
        addr.get("city"),
        addr.get("state"),
        addr.get("postal_code"),
        addr.get("country"),
    ]
    joined = ", ".join(p for p in parts if p)
    return joined or None


@payments_router.post("/create-checkout-session", response_model=ResponseModel)
async def create_checkout_session(body: CheckoutRequest):
    """Create a Stripe Checkout Session for an institution purchase.

    auto_renew=False -> one-time 90-day pass (mode="payment").
    auto_renew=True  -> annual auto-renewing subscription (mode="subscription").

    Payment is a precondition for signup: on success Stripe redirects to the
    institution signup page with the session id, which the backend verifies
    before creating the institution. No auth required here.
    """
    _require_stripe()

    price_id = _price_for(body.tier, body.auto_renew)
    mode = "subscription" if body.auto_renew else "payment"

    frontend = config.FRONTEND_URL.rstrip("/")
    params = {
        "mode": mode,
        # Do NOT set payment_method_types — let Stripe pick dynamically.
        "line_items": [{"price": price_id, "quantity": 1}],
        "billing_address_collection": "required",
        "metadata": {"tier": body.tier, "auto_renew": str(body.auto_renew).lower()},
        "success_url": (
            f"{frontend}/InstitutionSignup"
            "?checkout=success&session_id={CHECKOUT_SESSION_ID}"
        ),
        "cancel_url": f"{frontend}/Institutions?checkout=cancel",
    }
    # One-time payments don't create a Customer by default; force it so renewals
    # or future linkage have a customer to reference.
    if mode == "payment":
        params["customer_creation"] = "always"

    try:
        checkout = stripe.checkout.Session.create(**params)
    except stripe.error.StripeError as exc:
        logger.exception("Stripe checkout session creation failed")
        raise HTTPException(status_code=502, detail=str(exc))

    return ResponseModel(
        status="success",
        message="Checkout session created",
        data={"url": checkout.url},
    )


@payments_router.get("/checkout/{session_id}", response_model=ResponseModel)
async def get_checkout_session(
    session_id: str, session: Session = Depends(get_db)
):
    """Return verified details for a completed Checkout Session.

    Used by the signup page to pre-fill (and gray out) the buyer's email. Only
    returns details if the session is genuinely paid. Flags whether an
    institution has already been created from this session.
    """
    _require_stripe()

    try:
        # to_dict(): stripe v15 StripeObjects aren't dicts and lack .get();
        # to_dict() recursively yields plain dicts for the .get(...) access below.
        checkout = stripe.checkout.Session.retrieve(session_id).to_dict()
    except stripe.error.StripeError:
        raise HTTPException(status_code=404, detail="Checkout session not found")

    if checkout.get("payment_status") != "paid":
        raise HTTPException(status_code=402, detail="Payment not completed")

    already = session.exec(
        select(InstitutionSubscription).where(
            InstitutionSubscription.stripe_checkout_session_id == session_id
        )
    ).first()

    details = checkout.get("customer_details") or {}
    metadata = checkout.get("metadata") or {}
    return ResponseModel(
        status="success",
        message="Checkout session verified",
        data={
            "email": details.get("email"),
            "tier": metadata.get("tier"),
            "auto_renew": checkout.get("mode") == "subscription",
            "address": _format_address(details),
            "already_registered": already is not None,
        },
    )


@payments_router.post("/institution-signup", response_model=ResponseModel)
async def institution_signup(
    body: InstitutionSignupRequest, session: Session = Depends(get_db)
):
    """Create an institution after verifying its Stripe payment server-side.

    The buyer's email and Stripe IDs are taken from the retrieved session, never
    from the request body. A given paid session can create only one institution.
    """
    _require_stripe()

    try:
        checkout = stripe.checkout.Session.retrieve(body.session_id).to_dict()
    except stripe.error.StripeError:
        raise HTTPException(status_code=404, detail="Checkout session not found")

    if checkout.get("payment_status") != "paid":
        raise HTTPException(status_code=402, detail="Payment not completed")

    email = (checkout.get("customer_details") or {}).get("email")
    if not email:
        raise HTTPException(
            status_code=400, detail="Checkout session has no buyer email"
        )

    customer_id = checkout.get("customer")
    subscription_id = checkout.get("subscription")  # None for one-time payments
    auto_renew = checkout.get("mode") == "subscription"
    tier = (checkout.get("metadata") or {}).get("tier")

    # Determine access expiry: subscriptions track the billing period end;
    # one-time purchases get a fixed 90-day window.
    expiry = datetime.now(timezone.utc) + timedelta(days=ONE_OFF_DAYS)
    if subscription_id:
        try:
            sub = stripe.Subscription.retrieve(subscription_id).to_dict()
            period_end = _subscription_period_end(sub)
            if period_end:
                expiry = period_end
        except stripe.error.StripeError:
            logger.warning(
                "Could not retrieve subscription %s; using default expiry",
                subscription_id,
            )

    try:
        institution = create_paid_institution(
            session,
            name=body.name,
            contact_person=body.contact_person,
            contact_email=email,
            address=body.address,
            password=body.password,
            subscription_expiry=expiry,
            auto_renew=auto_renew,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            stripe_checkout_session_id=body.session_id,
            tier=tier,
        )
    except PaidSignupError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ResponseModel(
        status="success",
        message="Institution created",
        data={"institution_name": institution.name},
    )


@payments_router.post("/invoice-signup", response_model=ResponseModel)
async def invoice_signup(
    body: InvoiceSignupRequest, session: Session = Depends(get_db)
):
    """Create an invoiced annual subscription and grant access immediately.

    Unlike the card flows (Stripe Checkout first, signup form after), the
    institution is created here directly from the submitted form, then Stripe
    issues an emailed invoice (collection_method="send_invoice") for the annual
    price. Access is granted as soon as the invoice is issued; payment follows
    on net terms. The response returns Stripe's hosted invoice URL so the
    frontend can redirect the buyer to view and pay it.
    """
    _require_stripe()

    if not body.password or len(body.password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    # The invoiced plan bills the same annual recurring Price as the card
    # subscription; only the collection method differs.
    price_id = _price_for(body.tier, auto_renew=True)

    # Reject a duplicate name before creating any Stripe objects, so a failed
    # signup doesn't orphan a Stripe customer/subscription.
    name = body.institution_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Institution name cannot be empty")
    if session.exec(select(Institution).where(Institution.name == name)).first():
        raise HTTPException(
            status_code=400, detail=f"Institution with name '{name}' already exists"
        )

    try:
        customer = stripe.Customer.create(
            name=name,
            email=body.business_contact_email,
            address={"line1": body.institution_address},
            metadata={
                "tier": body.tier,
                "plan": "invoiced_annual",
                "teaching_contact_email": body.teaching_contact_email,
            },
        )
        # send_invoice + days_until_due => Stripe emails an invoice for the
        # annual Price instead of charging a card. The subscription is active
        # immediately; the invoice stays open until paid within net terms.
        sub = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": price_id}],
            collection_method="send_invoice",
            days_until_due=INVOICE_DUE_DAYS,
        ).to_dict()

        invoice_id = sub.get("latest_invoice")
        # Finalize so the invoice is issued (and emailed) right away rather than
        # waiting for Stripe's automatic finalization window.
        try:
            invoice = stripe.Invoice.finalize_invoice(invoice_id).to_dict()
        except stripe.error.StripeError:
            invoice = stripe.Invoice.retrieve(invoice_id).to_dict()
    except stripe.error.StripeError as exc:
        logger.exception("Stripe invoiced subscription creation failed")
        raise HTTPException(status_code=502, detail=str(exc))

    period_end = _subscription_period_end(sub)
    expiry = period_end or (datetime.now(timezone.utc) + timedelta(days=365))

    try:
        institution = create_invoiced_institution(
            session,
            institution_name=name,
            institution_address=body.institution_address,
            business_contact_name=body.business_contact_name,
            business_contact_email=body.business_contact_email,
            teaching_contact_name=body.teaching_contact_name,
            teaching_contact_email=body.teaching_contact_email,
            password=body.password,
            subscription_expiry=expiry,
            stripe_customer_id=customer.id,
            stripe_subscription_id=sub.get("id"),
            stripe_invoice_id=invoice.get("id"),
            tier=body.tier,
        )
    except PaidSignupError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ResponseModel(
        status="success",
        message="Invoiced institution created",
        data={
            "institution_name": institution.name,
            "hosted_invoice_url": invoice.get("hosted_invoice_url"),
        },
    )


@payments_router.post("/webhook")
async def stripe_webhook(request: Request, session: Session = Depends(get_db)):
    """Receive Stripe webhook events. Signature is verified against the raw body.

    Handles ongoing subscription lifecycle (renewals, cancellations, failed
    payments). Initial fulfillment happens at signup time, not here, because the
    institution row doesn't exist until the buyer completes the signup form.
    """
    if not config.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.warning("Stripe webhook: invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    # to_dict(): convert the StripeObject payload to plain dicts for .get() below.
    obj = event["data"]["object"].to_dict()

    if event_type == "invoice.paid":
        # Renewal (or the initial subscription invoice): extend the access
        # window to the new billing period end.
        sub_id = obj.get("subscription")
        period_end = None
        lines = (obj.get("lines") or {}).get("data") or []
        if lines:
            period_end = _utc_from_ts((lines[0].get("period") or {}).get("end"))
        _update_subscription_window(session, sub_id, period_end, active=True)

    elif event_type == "invoice.payment_failed":
        _set_subscription_active(session, obj.get("subscription"), active=False)

    elif event_type == "customer.subscription.deleted":
        _set_subscription_active(session, obj.get("id"), active=False)

    return {"received": True}


def _subscription_for_stripe_id(
    session: Session, sub_id: Optional[str]
) -> Optional[InstitutionSubscription]:
    if not sub_id:
        return None
    subscription = session.exec(
        select(InstitutionSubscription).where(
            InstitutionSubscription.stripe_subscription_id == sub_id
        )
    ).first()
    if not subscription:
        # Normal during the initial invoice: signup hasn't created the row yet.
        logger.info("No subscription record yet for stripe subscription %s", sub_id)
    return subscription


def _update_subscription_window(
    session: Session,
    sub_id: Optional[str],
    period_end: Optional[datetime],
    active: bool,
) -> None:
    subscription = _subscription_for_stripe_id(session, sub_id)
    if not subscription:
        return
    subscription.subscription_active = active
    if period_end:
        subscription.subscription_expiry = period_end
    session.add(subscription)
    session.commit()
    logger.info(
        "Subscription window updated: institution id=%s active=%s expiry=%s",
        subscription.institution_id,
        active,
        period_end,
    )


def _set_subscription_active(
    session: Session, sub_id: Optional[str], active: bool
) -> None:
    subscription = _subscription_for_stripe_id(session, sub_id)
    if not subscription:
        return
    subscription.subscription_active = active
    session.add(subscription)
    session.commit()
    logger.info(
        "Subscription active set: institution id=%s active=%s",
        subscription.institution_id,
        active,
    )
