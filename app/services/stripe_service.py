import logging

import stripe

from app.config import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    STRIPE_PRICE_ID_PRO,
    STRIPE_PRICE_ID_TEAM,
    FRONTEND_URL,
)

logger = logging.getLogger(__name__)

stripe.api_key = STRIPE_SECRET_KEY

PLAN_PRICE_IDS = {
    "pro": STRIPE_PRICE_ID_PRO,
    "team": STRIPE_PRICE_ID_TEAM,
}


class StripeNotConfigured(Exception):
    pass


def _require_configured():
    if not STRIPE_SECRET_KEY:
        raise StripeNotConfigured("Stripe is not configured on the server (missing STRIPE_SECRET_KEY).")


def create_checkout_session(plan: str, user_email: str, user_id: str, existing_customer_id: str | None) -> str:
    """Create a Stripe Checkout session for a subscription and return its URL."""
    _require_configured()
    price_id = PLAN_PRICE_IDS.get(plan)
    if not price_id:
        raise ValueError(f"Unknown or unconfigured plan: {plan}")

    session_kwargs = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{FRONTEND_URL.rstrip('/')}/pricing?checkout=success",
        "cancel_url": f"{FRONTEND_URL.rstrip('/')}/pricing?checkout=cancelled",
        "client_reference_id": user_id,
        "metadata": {"user_id": user_id, "plan": plan},
        "subscription_data": {"metadata": {"user_id": user_id, "plan": plan}},
    }
    if existing_customer_id:
        session_kwargs["customer"] = existing_customer_id
    else:
        session_kwargs["customer_email"] = user_email

    session = stripe.checkout.Session.create(**session_kwargs)
    return session.url


def create_billing_portal_session(customer_id: str) -> str:
    """Create a Stripe Customer Portal session (manage/cancel subscription) and return its URL."""
    _require_configured()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{FRONTEND_URL.rstrip('/')}/pricing",
    )
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str):
    """Verify and parse an incoming Stripe webhook. Raises on invalid signature."""
    if not STRIPE_WEBHOOK_SECRET:
        raise StripeNotConfigured("STRIPE_WEBHOOK_SECRET is not set.")
    return stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)


def plan_from_price_id(price_id: str) -> str | None:
    for plan, pid in PLAN_PRICE_IDS.items():
        if pid and pid == price_id:
            return plan
    return None
