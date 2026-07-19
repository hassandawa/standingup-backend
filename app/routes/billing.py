import logging
import secrets

from fastapi import APIRouter, Header, HTTPException, Request

from app.services.auth_service import (
    get_user_by_email_raw,
    get_user_by_id,
    get_user_by_token,
    set_subscription_id,
    update_subscription_status,
)
from app.services.flutterwave_service import (
    FlutterwaveNotConfigured,
    cancel_subscription,
    get_subscription_id_for_email,
    initiate_checkout,
    plan_from_amount,
    verify_transaction,
    verify_webhook_hash,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])

VALID_PLANS = {"pro", "team"}


def require_user(authorization: str = Header(default="")) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Sign in required.")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required.")
    return user


@router.post("/create-checkout-session")
def start_checkout(body: dict, authorization: str = Header(default="")):
    user = require_user(authorization)
    plan = (body or {}).get("plan", "")
    if plan not in VALID_PLANS:
        raise HTTPException(status_code=400, detail="plan must be 'pro' or 'team'.")
    tx_ref = f"su-{user['id']}-{plan}-{secrets.token_hex(6)}"
    try:
        url = initiate_checkout(
            plan=plan,
            user_email=user["email"],
            user_name=user["name"],
            tx_ref=tx_ref,
            meta={"user_id": user["id"], "plan": plan},
        )
        return {"url": url}
    except FlutterwaveNotConfigured as exc:
        logger.error("Checkout attempted while Flutterwave is not configured: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Online payments aren't available just yet. Send us a quick message below and we'll set you up manually.",
        )
    except Exception as exc:
        logger.error("Failed to create Flutterwave checkout: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start checkout. Please try again.")


@router.post("/verify-checkout")
def verify_checkout(body: dict, authorization: str = Header(default="")):
    """Called by the frontend right after Flutterwave redirects the user
    back, so the UI can reflect the new plan immediately rather than
    waiting on the webhook alone."""
    user = require_user(authorization)
    transaction_id = (body or {}).get("transaction_id", "")
    if not transaction_id:
        raise HTTPException(status_code=400, detail="transaction_id is required.")
    try:
        data = verify_transaction(transaction_id)
    except FlutterwaveNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Checkout verification failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not verify payment. It may still process shortly.")

    if data.get("status") != "successful":
        raise HTTPException(status_code=402, detail="Payment was not successful.")

    meta = data.get("meta") or {}
    plan = meta.get("plan") or plan_from_amount(data.get("amount"))
    if meta.get("user_id") != user["id"] or not plan:
        # Don't let one user's request confirm a different user's payment.
        raise HTTPException(status_code=403, detail="This payment does not belong to your account.")

    update_subscription_status(user["id"], plan, "active")
    sub_id = get_subscription_id_for_email(user["email"])
    if sub_id:
        set_subscription_id(user["id"], sub_id)

    return {"plan": plan, "status": "active"}


@router.post("/cancel-subscription")
def cancel(authorization: str = Header(default="")):
    user = require_user(authorization)
    from app.database import users
    from bson import ObjectId
    raw_user = users.find_one({"_id": ObjectId(user["id"])})
    sub_id = raw_user.get("flutterwave_subscription_id") if raw_user else None
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription found to cancel.")
    try:
        ok = cancel_subscription(sub_id)
    except FlutterwaveNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to cancel subscription. Please try again or contact support.")
    update_subscription_status(user["id"], "free", "cancelled")
    return {"plan": "free", "status": "cancelled"}


@router.post("/webhook")
async def flutterwave_webhook(request: Request, verif_hash: str = Header(default="", alias="verif-hash")):
    if not verify_webhook_hash(verif_hash):
        logger.warning("Invalid Flutterwave webhook hash received.")
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    body = await request.json()
    event = body.get("event", "")
    data = body.get("data", {})

    try:
        if event == "charge.completed" and data.get("status") == "successful":
            meta = data.get("meta") or {}
            customer_email = (data.get("customer") or {}).get("email")
            user_id = meta.get("user_id")
            plan = meta.get("plan") or plan_from_amount(data.get("amount"))

            user = None
            if user_id:
                user = get_user_by_id(user_id)
            if not user and customer_email:
                raw = get_user_by_email_raw(customer_email)
                user = {"id": str(raw["_id"])} if raw else None

            if user and plan:
                update_subscription_status(user["id"], plan, "active")
                sub_id = get_subscription_id_for_email(customer_email) if customer_email else None
                if sub_id:
                    set_subscription_id(user["id"], sub_id)
                logger.info("Flutterwave charge completed: user=%s plan=%s", user["id"], plan)

        elif event == "subscription.cancelled":
            customer_email = (data.get("customer") or {}).get("email")
            if customer_email:
                raw = get_user_by_email_raw(customer_email)
                if raw:
                    update_subscription_status(str(raw["_id"]), "free", "cancelled")
                    logger.info("Flutterwave subscription cancelled for %s -> downgraded to free", customer_email)

    except Exception as exc:
        logger.error("Error processing Flutterwave webhook %s: %s", event, exc, exc_info=True)
        # Return 200 anyway so Flutterwave doesn't endlessly retry; error is logged for follow-up.

    return {"received": True}
