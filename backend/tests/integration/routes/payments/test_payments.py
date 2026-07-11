"""Integration tests for the Stripe payment-gated institution flows.

Covers backend/routes/payments/payments_router.py (checkout, signup, invoice,
webhook), backend/routes/payments/payments_db.py (create_paid_institution /
create_invoiced_institution), and the GET /institution/subscription endpoint.

Stripe network calls are mocked at the individual-method level so the real
``stripe.error.*`` exception classes stay intact (replacing the whole stripe
module would make ``except stripe.error.StripeError`` catch a non-exception).
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import stripe
from sqlmodel import select

from backend import config
from backend.database.db_models import Institution, InstitutionSubscription, League
from backend.routes.auth.auth_core import create_access_token
from backend.routes.payments import payments_router as pr
from backend.routes.payments.payments_db import (
    PaidSignupError,
    create_invoiced_institution,
    create_paid_institution,
)
from backend.time_utils import utc_now

# A fixed future instant used wherever a Stripe period-end timestamp is needed.
FUTURE_DT = datetime(2027, 6, 1, tzinfo=timezone.utc)
FUTURE_TS = int(FUTURE_DT.timestamp())


def _stripe_obj(data: dict) -> MagicMock:
    """Mimic a stripe v15 StripeObject: callers do ``.to_dict()`` to get a dict."""
    obj = MagicMock()
    obj.to_dict.return_value = data
    return obj


def _paid_checkout(**overrides) -> dict:
    """A paid one-time Checkout Session payload (as returned by .to_dict())."""
    data = {
        "payment_status": "paid",
        "mode": "payment",
        "customer": "cus_test_1",
        "subscription": None,
        "customer_details": {
            "email": "buyer@university.edu",
            "address": {
                "line1": "1 Campus Rd",
                "city": "Perth",
                "state": "WA",
                "postal_code": "6000",
                "country": "AU",
            },
        },
        "metadata": {"tier": "club", "auto_renew": "false"},
    }
    data.update(overrides)
    return data


@pytest.fixture
def stripe_env(monkeypatch):
    """Configure Stripe secrets + tier price IDs so the guards pass in tests."""
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    monkeypatch.setattr(
        pr,
        "_TIER_PRICES",
        {
            ("club", False): "price_club_once",
            ("club", True): "price_club_year",
            ("university", False): "price_uni_once",
            ("university", True): "price_uni_year",
        },
    )


@pytest.fixture
def mock_stripe(stripe_env):
    """Patch every outbound Stripe call with sensible, overridable defaults."""
    with patch.object(pr.stripe.checkout.Session, "create") as checkout_create, patch.object(
        pr.stripe.checkout.Session, "retrieve"
    ) as checkout_retrieve, patch.object(
        pr.stripe.Subscription, "create"
    ) as sub_create, patch.object(
        pr.stripe.Subscription, "retrieve"
    ) as sub_retrieve, patch.object(
        pr.stripe.Customer, "create"
    ) as cust_create, patch.object(
        pr.stripe.Invoice, "finalize_invoice"
    ) as inv_finalize, patch.object(
        pr.stripe.Invoice, "retrieve"
    ) as inv_retrieve, patch.object(
        pr.stripe.Webhook, "construct_event"
    ) as webhook:
        checkout_create.return_value = MagicMock(url="https://checkout.test/cs_1")
        checkout_retrieve.return_value = _stripe_obj(_paid_checkout())
        # Subscription with only a top-level current_period_end (no items) to
        # exercise the fallback path in _subscription_period_end.
        sub_retrieve.return_value = _stripe_obj({"current_period_end": FUTURE_TS})
        # Subscription create returns items[0].current_period_end (primary path).
        sub_create.return_value = _stripe_obj(
            {
                "id": "sub_inv_1",
                "latest_invoice": "in_1",
                "items": {"data": [{"current_period_end": FUTURE_TS}]},
            }
        )
        cust_create.return_value = MagicMock(id="cus_inv_1")
        inv_finalize.return_value = _stripe_obj(
            {"id": "in_1", "hosted_invoice_url": "https://invoice.test/in_1"}
        )
        inv_retrieve.return_value = _stripe_obj(
            {"id": "in_1", "hosted_invoice_url": "https://invoice.test/in_1"}
        )
        yield SimpleNamespace(
            checkout_create=checkout_create,
            checkout_retrieve=checkout_retrieve,
            sub_create=sub_create,
            sub_retrieve=sub_retrieve,
            cust_create=cust_create,
            inv_finalize=inv_finalize,
            inv_retrieve=inv_retrieve,
            webhook=webhook,
        )


# --------------------------------------------------------------------------- #
# POST /payments/create-checkout-session
# --------------------------------------------------------------------------- #


def test_create_checkout_one_time(client, mock_stripe):
    resp = client.post(
        "/payments/create-checkout-session",
        json={"tier": "club", "auto_renew": False},
    )
    assert resp.status_code == 200
    assert resp.json()["url"] == "https://checkout.test/cs_1"

    params = mock_stripe.checkout_create.call_args.kwargs
    assert params["mode"] == "payment"
    assert params["customer_creation"] == "always"
    assert params["line_items"] == [{"price": "price_club_once", "quantity": 1}]


def test_create_checkout_subscription(client, mock_stripe):
    resp = client.post(
        "/payments/create-checkout-session",
        json={"tier": "university", "auto_renew": True},
    )
    assert resp.status_code == 200
    params = mock_stripe.checkout_create.call_args.kwargs
    assert params["mode"] == "subscription"
    assert "customer_creation" not in params
    assert params["line_items"] == [{"price": "price_uni_year", "quantity": 1}]


def test_create_checkout_unknown_tier(client, mock_stripe):
    resp = client.post(
        "/payments/create-checkout-session",
        json={"tier": "enterprise", "auto_renew": False},
    )
    assert resp.status_code == 400
    assert "tier" in resp.json()["detail"].lower()


def test_create_checkout_not_configured(client, monkeypatch):
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", None)
    resp = client.post(
        "/payments/create-checkout-session",
        json={"tier": "club", "auto_renew": False},
    )
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Stripe is not configured"


def test_create_checkout_stripe_error(client, mock_stripe):
    mock_stripe.checkout_create.side_effect = stripe.error.StripeError("boom")
    resp = client.post(
        "/payments/create-checkout-session",
        json={"tier": "club", "auto_renew": False},
    )
    assert resp.status_code == 502


# --------------------------------------------------------------------------- #
# GET /payments/checkout/{session_id}
# --------------------------------------------------------------------------- #


def test_get_checkout_paid(client, mock_stripe):
    resp = client.get("/payments/checkout/cs_paid")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "buyer@university.edu"
    assert data["tier"] == "club"
    assert data["auto_renew"] is False
    assert "1 Campus Rd" in data["address"]
    assert data["already_registered"] is False


def test_get_checkout_already_registered(client, db_session, mock_stripe):
    create_paid_institution(
        db_session,
        name="Already U",
        contact_person="C",
        contact_email="buyer@university.edu",
        address=None,
        password="pw",
        subscription_expiry=FUTURE_DT,
        auto_renew=False,
        stripe_customer_id="cus_x",
        stripe_subscription_id=None,
        stripe_checkout_session_id="cs_dup",
        tier="club",
    )
    resp = client.get("/payments/checkout/cs_dup")
    assert resp.status_code == 200
    assert resp.json()["already_registered"] is True


def test_get_checkout_not_paid(client, mock_stripe):
    mock_stripe.checkout_retrieve.return_value = _stripe_obj(
        _paid_checkout(payment_status="unpaid")
    )
    resp = client.get("/payments/checkout/cs_unpaid")
    assert resp.status_code == 402


def test_get_checkout_unknown_session(client, mock_stripe):
    mock_stripe.checkout_retrieve.side_effect = stripe.error.InvalidRequestError(
        "no such session", param="id"
    )
    resp = client.get("/payments/checkout/cs_missing")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# POST /payments/institution-signup
# --------------------------------------------------------------------------- #


def test_institution_signup_one_time(client, db_session, mock_stripe):
    resp = client.post(
        "/payments/institution-signup",
        json={
            "session_id": "cs_signup_1",
            "name": "Signup College",
            "contact_person": "Teacher",
            "address": "10 School St",
            "password": "longpassword",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["institution_name"] == "Signup College"
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    inst = db_session.exec(
        select(Institution).where(Institution.name == "Signup College")
    ).first()
    assert inst is not None
    # Email comes from the verified session, never the request body.
    assert inst.contact_email == "buyer@university.edu"
    # One-time payment => fixed 90-day window, not the subscription period end.
    expected = utc_now() + timedelta(days=pr.ONE_OFF_DAYS)
    assert abs((inst.subscription.subscription_expiry - expected).total_seconds()) < 60
    assert inst.subscription.payment_method == "card"
    assert inst.subscription.auto_renew is False
    # An "unassigned" league is provisioned for every new institution.
    league = db_session.exec(
        select(League).where(League.institution_id == inst.id)
    ).first()
    assert league is not None and league.name == "unassigned"


def test_institution_signup_subscription_uses_period_end(client, db_session, mock_stripe):
    mock_stripe.checkout_retrieve.return_value = _stripe_obj(
        _paid_checkout(mode="subscription", subscription="sub_1")
    )
    resp = client.post(
        "/payments/institution-signup",
        json={
            "session_id": "cs_signup_sub",
            "name": "Sub College",
            "contact_person": "Teacher",
            "password": "longpassword",
        },
    )
    assert resp.status_code == 200
    inst = db_session.exec(
        select(Institution).where(Institution.name == "Sub College")
    ).first()
    assert inst.subscription.auto_renew is True
    # Expiry tracks the subscription's current_period_end (fallback field path).
    assert abs((inst.subscription.subscription_expiry - FUTURE_DT).total_seconds()) < 2
    mock_stripe.sub_retrieve.assert_called_once_with("sub_1")


def test_institution_signup_subscription_retrieve_failure_defaults(
    client, db_session, mock_stripe
):
    mock_stripe.checkout_retrieve.return_value = _stripe_obj(
        _paid_checkout(mode="subscription", subscription="sub_err")
    )
    mock_stripe.sub_retrieve.side_effect = stripe.error.StripeError("down")
    resp = client.post(
        "/payments/institution-signup",
        json={
            "session_id": "cs_signup_suberr",
            "name": "Sub Err College",
            "contact_person": "Teacher",
            "password": "longpassword",
        },
    )
    assert resp.status_code == 200
    inst = db_session.exec(
        select(Institution).where(Institution.name == "Sub Err College")
    ).first()
    # Falls back to the 90-day default when the subscription can't be read.
    expected = utc_now() + timedelta(days=pr.ONE_OFF_DAYS)
    assert abs((inst.subscription.subscription_expiry - expected).total_seconds()) < 60


def test_institution_signup_not_paid(client, mock_stripe):
    mock_stripe.checkout_retrieve.return_value = _stripe_obj(
        _paid_checkout(payment_status="unpaid")
    )
    resp = client.post(
        "/payments/institution-signup",
        json={
            "session_id": "cs_np",
            "name": "Nope College",
            "contact_person": "T",
            "password": "longpassword",
        },
    )
    assert resp.status_code == 402


def test_institution_signup_no_email(client, mock_stripe):
    mock_stripe.checkout_retrieve.return_value = _stripe_obj(
        _paid_checkout(customer_details={})
    )
    resp = client.post(
        "/payments/institution-signup",
        json={
            "session_id": "cs_noemail",
            "name": "NoEmail College",
            "contact_person": "T",
            "password": "longpassword",
        },
    )
    assert resp.status_code == 400


def test_institution_signup_unknown_session(client, mock_stripe):
    mock_stripe.checkout_retrieve.side_effect = stripe.error.InvalidRequestError(
        "no such session", param="id"
    )
    resp = client.post(
        "/payments/institution-signup",
        json={
            "session_id": "cs_gone",
            "name": "Gone College",
            "contact_person": "T",
            "password": "longpassword",
        },
    )
    assert resp.status_code == 404


def test_institution_signup_is_idempotent(client, db_session, mock_stripe):
    payload = {
        "session_id": "cs_idem",
        "name": "Idem College",
        "contact_person": "T",
        "password": "longpassword",
    }
    first = client.post("/payments/institution-signup", json=payload)
    second = client.post("/payments/institution-signup", json=payload)
    assert first.status_code == 200 and second.status_code == 200
    # Replay returns the same institution, never a duplicate.
    insts = db_session.exec(
        select(Institution).where(Institution.name == "Idem College")
    ).all()
    assert len(insts) == 1
    subs = db_session.exec(
        select(InstitutionSubscription).where(
            InstitutionSubscription.stripe_checkout_session_id == "cs_idem"
        )
    ).all()
    assert len(subs) == 1


def test_institution_signup_duplicate_name(client, db_session, mock_stripe):
    create_paid_institution(
        db_session,
        name="Clash College",
        contact_person="C",
        contact_email="buyer@university.edu",
        address=None,
        password="pw",
        subscription_expiry=FUTURE_DT,
        auto_renew=False,
        stripe_customer_id=None,
        stripe_subscription_id=None,
        stripe_checkout_session_id="cs_first",
        tier="club",
    )
    resp = client.post(
        "/payments/institution-signup",
        json={
            "session_id": "cs_second",  # different paid session, same name
            "name": "Clash College",
            "contact_person": "T",
            "password": "longpassword",
        },
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


# --------------------------------------------------------------------------- #
# POST /payments/invoice-signup
# --------------------------------------------------------------------------- #


def _invoice_payload(**overrides) -> dict:
    payload = {
        "tier": "university",
        "institution_name": "Invoice University",
        "institution_address": "5 Quad",
        "business_contact_name": "Bursar",
        "business_contact_email": "bursar@uni.edu",
        "teaching_contact_name": "Lecturer",
        "teaching_contact_email": "lecturer@uni.edu",
        "password": "longpassword",
    }
    payload.update(overrides)
    return payload


def test_invoice_signup_success(client, db_session, mock_stripe):
    resp = client.post("/payments/invoice-signup", json=_invoice_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["institution_name"] == "Invoice University"
    assert body["hosted_invoice_url"] == "https://invoice.test/in_1"
    assert body["access_token"]

    inst = db_session.exec(
        select(Institution).where(Institution.name == "Invoice University")
    ).first()
    sub = inst.subscription
    assert sub.payment_method == "invoice"
    assert sub.auto_renew is True
    # Teaching contact is the login; business contact kept separately for billing.
    assert inst.contact_email == "lecturer@uni.edu"
    assert sub.business_contact_email == "bursar@uni.edu"
    # Expiry tracks items[0].current_period_end (primary path).
    assert abs((sub.subscription_expiry - FUTURE_DT).total_seconds()) < 2

    invoice_args = mock_stripe.sub_create.call_args.kwargs
    assert invoice_args["collection_method"] == "send_invoice"
    assert invoice_args["days_until_due"] == pr.INVOICE_DUE_DAYS


def test_invoice_signup_finalize_fallback(client, db_session, mock_stripe):
    # Finalize fails (already finalized) -> fall back to Invoice.retrieve.
    mock_stripe.inv_finalize.side_effect = stripe.error.StripeError("already final")
    mock_stripe.inv_retrieve.return_value = _stripe_obj(
        {"id": "in_1", "hosted_invoice_url": "https://invoice.test/retrieved"}
    )
    resp = client.post(
        "/payments/invoice-signup", json=_invoice_payload(institution_name="Fallback U")
    )
    assert resp.status_code == 200
    assert resp.json()["hosted_invoice_url"] == "https://invoice.test/retrieved"
    mock_stripe.inv_retrieve.assert_called_once()


def test_invoice_signup_short_password(client, mock_stripe):
    resp = client.post("/payments/invoice-signup", json=_invoice_payload(password="short"))
    assert resp.status_code == 400
    assert "8 characters" in resp.json()["detail"]
    mock_stripe.cust_create.assert_not_called()


def test_invoice_signup_empty_name(client, mock_stripe):
    resp = client.post(
        "/payments/invoice-signup", json=_invoice_payload(institution_name="   ")
    )
    assert resp.status_code == 400
    mock_stripe.cust_create.assert_not_called()


def test_invoice_signup_duplicate_name(client, db_session, mock_stripe):
    create_paid_institution(
        db_session,
        name="Dup Invoice U",
        contact_person="C",
        contact_email="x@uni.edu",
        address=None,
        password="pw",
        subscription_expiry=FUTURE_DT,
        auto_renew=False,
        stripe_customer_id=None,
        stripe_subscription_id=None,
        stripe_checkout_session_id="cs_di",
        tier="club",
    )
    resp = client.post(
        "/payments/invoice-signup", json=_invoice_payload(institution_name="Dup Invoice U")
    )
    assert resp.status_code == 409
    # Name rejected before any Stripe objects are created.
    mock_stripe.cust_create.assert_not_called()


def test_invoice_signup_stripe_error(client, mock_stripe):
    mock_stripe.cust_create.side_effect = stripe.error.StripeError("card_declined")
    resp = client.post(
        "/payments/invoice-signup", json=_invoice_payload(institution_name="Err Invoice U")
    )
    assert resp.status_code == 502


def test_invoice_signup_not_configured(client, monkeypatch):
    monkeypatch.setattr(config, "STRIPE_SECRET_KEY", None)
    resp = client.post("/payments/invoice-signup", json=_invoice_payload())
    assert resp.status_code == 500


def test_invoice_signup_db_error_maps_to_400(client, mock_stripe):
    # Stripe objects created, but the DB layer rejects the signup (defensive
    # guard duplicating the pre-check) -> surfaced as a 400.
    with patch.object(
        pr, "create_invoiced_institution", side_effect=PaidSignupError("nope")
    ):
        resp = client.post(
            "/payments/invoice-signup", json=_invoice_payload(institution_name="DbErr U")
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "nope"


# --------------------------------------------------------------------------- #
# POST /payments/webhook
# --------------------------------------------------------------------------- #


def _make_card_sub(db_session, sub_id="sub_hook", active=True, expiry=None):
    inst = create_paid_institution(
        db_session,
        name=f"Hook College {sub_id}",
        contact_person="C",
        contact_email="hook@uni.edu",
        address=None,
        password="pw",
        subscription_expiry=expiry or (utc_now() - timedelta(days=1)),
        auto_renew=True,
        stripe_customer_id="cus_hook",
        stripe_subscription_id=sub_id,
        stripe_checkout_session_id=f"cs_{sub_id}",
        tier="club",
    )
    sub = inst.subscription
    sub.subscription_active = active
    db_session.add(sub)
    db_session.commit()
    return inst


def _webhook_event(event_type, obj):
    return {"type": event_type, "data": {"object": _stripe_obj(obj)}}


def test_webhook_invoice_paid_extends_window(client, db_session, mock_stripe):
    inst = _make_card_sub(db_session, sub_id="sub_paid", active=False)
    mock_stripe.webhook.return_value = _webhook_event(
        "invoice.paid",
        {
            "subscription": "sub_paid",
            "lines": {"data": [{"period": {"end": FUTURE_TS}}]},
        },
    )
    resp = client.post(
        "/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"}
    )
    assert resp.status_code == 200
    assert resp.json()["received"] is True

    db_session.expire_all()
    sub = db_session.get(Institution, inst.id).subscription
    assert sub.subscription_active is True
    assert abs((sub.subscription_expiry - FUTURE_DT).total_seconds()) < 2


def test_webhook_invoice_paid_no_period_keeps_expiry(client, db_session, mock_stripe):
    original = datetime(2026, 1, 1, tzinfo=timezone.utc)
    inst = _make_card_sub(db_session, sub_id="sub_noperiod", active=False, expiry=original)
    mock_stripe.webhook.return_value = _webhook_event(
        "invoice.paid", {"subscription": "sub_noperiod", "lines": {"data": []}}
    )
    resp = client.post(
        "/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"}
    )
    assert resp.status_code == 200

    db_session.expire_all()
    sub = db_session.get(Institution, inst.id).subscription
    assert sub.subscription_active is True  # reactivated
    assert abs((sub.subscription_expiry - original).total_seconds()) < 2  # unchanged


def test_webhook_payment_failed_deactivates(client, db_session, mock_stripe):
    inst = _make_card_sub(db_session, sub_id="sub_fail", active=True)
    mock_stripe.webhook.return_value = _webhook_event(
        "invoice.payment_failed", {"subscription": "sub_fail"}
    )
    resp = client.post(
        "/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"}
    )
    assert resp.status_code == 200
    db_session.expire_all()
    assert db_session.get(Institution, inst.id).subscription.subscription_active is False


def test_webhook_subscription_deleted_deactivates(client, db_session, mock_stripe):
    inst = _make_card_sub(db_session, sub_id="sub_del", active=True)
    mock_stripe.webhook.return_value = _webhook_event(
        "customer.subscription.deleted", {"id": "sub_del"}
    )
    resp = client.post(
        "/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"}
    )
    assert resp.status_code == 200
    db_session.expire_all()
    assert db_session.get(Institution, inst.id).subscription.subscription_active is False


def test_webhook_unknown_subscription_is_noop(client, mock_stripe):
    mock_stripe.webhook.return_value = _webhook_event(
        "invoice.payment_failed", {"subscription": "sub_nonexistent"}
    )
    resp = client.post(
        "/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"}
    )
    assert resp.status_code == 200
    assert resp.json()["received"] is True


def test_webhook_invoice_paid_unknown_subscription_is_noop(client, mock_stripe):
    # invoice.paid for a subscription with no local row: the update path no-ops.
    mock_stripe.webhook.return_value = _webhook_event(
        "invoice.paid",
        {"subscription": "sub_ghost", "lines": {"data": [{"period": {"end": FUTURE_TS}}]}},
    )
    resp = client.post(
        "/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"}
    )
    assert resp.status_code == 200
    assert resp.json()["received"] is True


def test_webhook_invoice_paid_null_subscription_and_period(client, mock_stripe):
    # No subscription id and a null period end exercise the early-return guards.
    mock_stripe.webhook.return_value = _webhook_event(
        "invoice.paid", {"lines": {"data": [{"period": {"end": None}}]}}
    )
    resp = client.post(
        "/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"}
    )
    assert resp.status_code == 200
    assert resp.json()["received"] is True


def test_webhook_unhandled_event_ignored(client, mock_stripe):
    mock_stripe.webhook.return_value = _webhook_event(
        "customer.created", {"id": "cus_xyz"}
    )
    resp = client.post(
        "/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"}
    )
    assert resp.status_code == 200
    assert resp.json()["received"] is True


def test_webhook_invalid_payload(client, mock_stripe):
    mock_stripe.webhook.side_effect = ValueError("bad json")
    resp = client.post(
        "/payments/webhook", content=b"not-json", headers={"stripe-signature": "sig"}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid payload"


def test_webhook_invalid_signature(client, mock_stripe):
    mock_stripe.webhook.side_effect = stripe.error.SignatureVerificationError(
        "bad sig", "sig-header"
    )
    resp = client.post(
        "/payments/webhook", content=b"{}", headers={"stripe-signature": "bad"}
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid signature"


def test_webhook_no_secret_configured(client, monkeypatch):
    monkeypatch.setattr(config, "STRIPE_WEBHOOK_SECRET", None)
    resp = client.post(
        "/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"}
    )
    assert resp.status_code == 500


# --------------------------------------------------------------------------- #
# payments_db helpers (direct, no HTTP / no Stripe)
# --------------------------------------------------------------------------- #


def test_create_paid_institution_persists_records(db_session):
    inst = create_paid_institution(
        db_session,
        name="Direct Paid U",
        contact_person="Person",
        contact_email="p@uni.edu",
        address="addr",
        password="pw",
        subscription_expiry=FUTURE_DT,
        auto_renew=True,
        stripe_customer_id="cus_d",
        stripe_subscription_id="sub_d",
        stripe_checkout_session_id="cs_direct",
        tier="university",
    )
    assert inst.id is not None
    assert inst.subscription.tier == "university"
    assert inst.subscription.payment_method == "card"
    assert inst.subscription.subscription_active is True
    assert inst.verify_password("pw")
    league = db_session.exec(
        select(League).where(League.institution_id == inst.id)
    ).first()
    assert league.name == "unassigned"


def test_create_paid_institution_replay_returns_existing(db_session):
    kwargs = dict(
        contact_person="Person",
        contact_email="p@uni.edu",
        address=None,
        password="pw",
        subscription_expiry=FUTURE_DT,
        auto_renew=False,
        stripe_customer_id="cus_d",
        stripe_subscription_id=None,
        stripe_checkout_session_id="cs_replay",
        tier="club",
    )
    first = create_paid_institution(db_session, name="Replay U", **kwargs)
    # Same session id, even a different name, returns the original institution.
    second = create_paid_institution(db_session, name="Different Name", **kwargs)
    assert first.id == second.id
    assert (
        db_session.exec(select(Institution).where(Institution.name == "Different Name")).first()
        is None
    )


def test_create_paid_institution_empty_name(db_session):
    with pytest.raises(PaidSignupError):
        create_paid_institution(
            db_session,
            name="   ",
            contact_person="P",
            contact_email="p@uni.edu",
            address=None,
            password="pw",
            subscription_expiry=FUTURE_DT,
            auto_renew=False,
            stripe_customer_id=None,
            stripe_subscription_id=None,
            stripe_checkout_session_id="cs_empty",
        )


def test_create_paid_institution_duplicate_name(db_session):
    create_paid_institution(
        db_session,
        name="DupDirect U",
        contact_person="P",
        contact_email="p@uni.edu",
        address=None,
        password="pw",
        subscription_expiry=FUTURE_DT,
        auto_renew=False,
        stripe_customer_id=None,
        stripe_subscription_id=None,
        stripe_checkout_session_id="cs_one",
    )
    with pytest.raises(PaidSignupError, match="already exists"):
        create_paid_institution(
            db_session,
            name="DupDirect U",
            contact_person="P",
            contact_email="p@uni.edu",
            address=None,
            password="pw",
            subscription_expiry=FUTURE_DT,
            auto_renew=False,
            stripe_customer_id=None,
            stripe_subscription_id=None,
            stripe_checkout_session_id="cs_two",
        )


def test_create_invoiced_institution_persists_records(db_session):
    inst = create_invoiced_institution(
        db_session,
        institution_name="Direct Invoice U",
        institution_address="addr",
        business_contact_name="Bursar",
        business_contact_email="bursar@uni.edu",
        teaching_contact_name="Lecturer",
        teaching_contact_email="lecturer@uni.edu",
        password="pw",
        subscription_expiry=FUTURE_DT,
        stripe_customer_id="cus_i",
        stripe_subscription_id="sub_i",
        stripe_invoice_id="in_i",
        tier="university",
    )
    sub = inst.subscription
    assert sub.payment_method == "invoice"
    assert sub.auto_renew is True
    assert sub.stripe_invoice_id == "in_i"
    # Teaching contact is the institution login; business contact billing-only.
    assert inst.contact_person == "Lecturer"
    assert inst.contact_email == "lecturer@uni.edu"
    assert sub.business_contact_email == "bursar@uni.edu"


def test_create_invoiced_institution_empty_name(db_session):
    with pytest.raises(PaidSignupError, match="cannot be empty"):
        create_invoiced_institution(
            db_session,
            institution_name="   ",
            institution_address="a",
            business_contact_name="B",
            business_contact_email="b@uni.edu",
            teaching_contact_name="T",
            teaching_contact_email="t@uni.edu",
            password="pw",
            subscription_expiry=FUTURE_DT,
            stripe_customer_id=None,
            stripe_subscription_id=None,
            stripe_invoice_id=None,
        )


def test_create_invoiced_institution_duplicate_name(db_session):
    create_invoiced_institution(
        db_session,
        institution_name="DupInv U",
        institution_address="a",
        business_contact_name="B",
        business_contact_email="b@uni.edu",
        teaching_contact_name="T",
        teaching_contact_email="t@uni.edu",
        password="pw",
        subscription_expiry=FUTURE_DT,
        stripe_customer_id=None,
        stripe_subscription_id=None,
        stripe_invoice_id=None,
    )
    with pytest.raises(PaidSignupError, match="already exists"):
        create_invoiced_institution(
            db_session,
            institution_name="DupInv U",
            institution_address="a",
            business_contact_name="B",
            business_contact_email="b@uni.edu",
            teaching_contact_name="T",
            teaching_contact_email="t@uni.edu",
            password="pw",
            subscription_expiry=FUTURE_DT,
            stripe_customer_id=None,
            stripe_subscription_id=None,
            stripe_invoice_id=None,
        )


# --------------------------------------------------------------------------- #
# GET /institution/subscription
# --------------------------------------------------------------------------- #


def test_get_subscription_returns_details(client, institution_headers):
    resp = client.get("/institution/subscription", headers=institution_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["institution_name"] == "test_institution"
    assert data["subscription"] is not None
    assert data["subscription"]["payment_method"] == "admin"
    assert data["subscription"]["subscription_active"] is True


def test_get_subscription_no_subscription_row(client, db_session):
    # Institution created without a subscription record exercises the None branch.
    inst = Institution(
        name="No Sub Inst",
        contact_person="P",
        contact_email="p@uni.edu",
        created_date=utc_now(),
        password_hash="hash",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    token = create_access_token(
        data={"sub": inst.name, "role": "institution", "institution_id": inst.id},
        expires_delta=timedelta(minutes=30),
    )
    resp = client.get(
        "/institution/subscription", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["subscription"] is None


def test_get_subscription_requires_auth(client):
    resp = client.get("/institution/subscription")
    assert resp.status_code in (401, 403)
