import logging

import requests

from app.config import (
    FLUTTERWAVE_SECRET_KEY,
    FLUTTERWAVE_WEBHOOK_HASH,
    FLUTTERWAVE_PLAN_ID_PRO,
    FLUTTERWAVE_PLAN_ID_TEAM,
    FLUTTERWAVE_CURRENCY,
    PLAN_AMOUNTS,
    FRONTEND_URL,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.flutterwave.com/v3"

PLAN_IDS = {
    "pro": FLUTTERWAVE_PLAN_ID_PRO,
    "team": FLUTTERWAVE_PLAN_ID_TEAM,
}


class FlutterwaveNotConfigured(Exception):
    pass


def _require_configured():
    if not FLUTTERWAVE_SECRET_KEY:
        raise FlutterwaveNotConfigured("Flutterwave is not configured on the server (missing FLUTTERWAVE_SECRET_KEY).")


def _headers():
    return {
        "Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initiate_checkout(plan: str, user_email: str, user_name: str, tx_ref: str, meta: dict) -> str:
    """Create a Flutterwave hosted checkout link for a subscription payment
    tied to a recurring payment plan. Returns the checkout URL to redirect
    the user to."""
    _require_configured()
    plan_id = PLAN_IDS.get(plan)
    amount = PLAN_AMOUNTS.get(plan)
    if not plan_id or not amount:
        raise ValueError(f"Unknown or unconfigured plan: {plan}")

    payload = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": FLUTTERWAVE_CURRENCY,
        "redirect_url": f"{FRONTEND_URL.rstrip('/')}/pricing",
        "payment_plan": plan_id,
        "meta": meta,
        "customer": {
            "email": user_email,
            "name": user_name or user_email,
        },
        "customizations": {
            "title": "startingUP subscription",
            "description": f"{plan.capitalize()} plan subscription",
        },
    }
    resp = requests.post(f"{BASE_URL}/payments", json=payload, headers=_headers(), timeout=15)
    data = resp.json()
    if resp.status_code >= 400 or data.get("status") != "success":
        logger.error("Flutterwave checkout init failed: %s", data)
        raise RuntimeError(data.get("message", "Failed to start Flutterwave checkout."))
    return data["data"]["link"]


def verify_transaction(transaction_id: str) -> dict:
    """Verify a completed transaction directly with Flutterwave (used for
    the immediate redirect-back confirmation, independent of webhooks)."""
    _require_configured()
    resp = requests.get(f"{BASE_URL}/transactions/{transaction_id}/verify", headers=_headers(), timeout=15)
    data = resp.json()
    if resp.status_code >= 400 or data.get("status") != "success":
        logger.error("Flutterwave verify failed: %s", data)
        raise RuntimeError(data.get("message", "Failed to verify transaction."))
    return data["data"]


def get_subscription_id_for_email(email: str) -> str | None:
    """Look up the most recent active subscription for a customer email,
    used right after their first successful payment so we can store the
    subscription ID for later self-service cancellation."""
    _require_configured()
    resp = requests.get(f"{BASE_URL}/subscriptions", params={"email": email}, headers=_headers(), timeout=15)
    data = resp.json()
    if resp.status_code >= 400 or data.get("status") != "success":
        logger.warning("Flutterwave subscription lookup failed for %s: %s", email, data)
        return None
    subs = data.get("data", [])
    if not subs:
        return None
    # Most recent first
    return str(subs[0].get("id")) if subs[0].get("id") else None


def cancel_subscription(subscription_id: str) -> bool:
    _require_configured()
    resp = requests.put(f"{BASE_URL}/subscriptions/{subscription_id}/cancel", headers=_headers(), timeout=15)
    data = resp.json()
    if resp.status_code >= 400 or data.get("status") != "success":
        logger.error("Flutterwave cancel subscription failed: %s", data)
        return False
    return True


def verify_webhook_hash(received_hash: str) -> bool:
    """Flutterwave webhooks are authenticated with a simple shared-secret
    header (the 'verif-hash' you set in your Flutterwave dashboard), not an
    HMAC signature like Stripe."""
    if not FLUTTERWAVE_WEBHOOK_HASH:
        return False
    return received_hash == FLUTTERWAVE_WEBHOOK_HASH


def plan_from_amount(amount) -> str | None:
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return None
    for plan, plan_amount in PLAN_AMOUNTS.items():
        if abs(amount - plan_amount) < 0.01:
            return plan
    return None
