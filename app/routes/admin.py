import logging

from fastapi import APIRouter, Header, HTTPException

from app.config import ADMIN_EMAILS
from app.database import (
    ai_cofounder_chats,
    business_plans,
    customer_insights,
    decision_reports,
    development_hubs,
    financial_plans,
    growth_hubs,
    investor_tools,
    launch_hubs,
    market_intelligence,
    marketing_hub,
    saved_analyses,
    saved_ideas,
    startup_plans,
    users,
)
from app.services.auth_service import get_user_by_token, admin_set_plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Collections that represent a user actually *doing* something in the app
# (generating a plan, saving analysis, etc.) — used to build the activity
# summary shown per user in the admin dashboard.
ACTIVITY_COLLECTIONS = {
    "startup_plans": startup_plans,
    "saved_analyses": saved_analyses,
    "business_plans": business_plans,
    "investor_tools": investor_tools,
    "decision_reports": decision_reports,
    "customer_insights": customer_insights,
    "market_intelligence": market_intelligence,
    "ai_cofounder_chats": ai_cofounder_chats,
    "financial_plans": financial_plans,
    "growth_hubs": growth_hubs,
    "marketing_hub": marketing_hub,
    "development_hubs": development_hubs,
    "launch_hubs": launch_hubs,
}


def require_admin(authorization: str = Header(default="")) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Sign in required.")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required.")
    if user["email"].lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def _serialize_user(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name", ""),
        "email": doc.get("email", ""),
        "plan": doc.get("plan", "free"),
        "subscription_status": doc.get("subscription_status"),
        "plan_expires_at": doc.get("plan_expires_at"),
        "ideas_generated_count": doc.get("ideas_generated_count", 0),
        "created_at": doc.get("created_at"),
    }


@router.get("/users")
def list_users(authorization: str = Header(default="")):
    require_admin(authorization)
    all_users = users.find({})
    result = sorted(
        (_serialize_user(u) for u in all_users),
        key=lambda u: u["created_at"] or "",
        reverse=True,
    )
    return {"users": result, "total": len(result)}


@router.post("/users/{user_id}/set-plan")
def set_user_plan(user_id: str, body: dict, authorization: str = Header(default="")):
    require_admin(authorization)
    plan = (body or {}).get("plan", "")
    if plan not in ("free", "pro", "team"):
        raise HTTPException(status_code=400, detail="plan must be 'free', 'pro', or 'team'.")
    days = (body or {}).get("days")
    if days is not None:
        try:
            days = int(days)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="days must be a whole number.")
    try:
        admin_set_plan(user_id, plan, days)
    except Exception as exc:
        logger.error("Failed to set plan for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update plan.")
    return {"message": f"Plan updated to {plan}."}


@router.get("/users/{user_id}/activity")
def get_user_activity(user_id: str, authorization: str = Header(default="")):
    require_admin(authorization)

    counts = {}
    for name, collection in ACTIVITY_COLLECTIONS.items():
        try:
            counts[name] = collection.count_documents({"user_id": user_id})
        except Exception:
            counts[name] = 0

    try:
        saved = list(saved_ideas.find({"user_id": user_id}).sort("created_at", -1))
    except Exception:
        saved = []

    saved_summary = [
        {
            "id": str(doc.get("_id")),
            "title": doc.get("title") or "Untitled",
            "created_at": doc.get("created_at"),
        }
        for doc in saved
    ]

    return {
        "activity_counts": counts,
        "total_activity": sum(counts.values()),
        "saved_ideas": saved_summary,
        "saved_ideas_count": len(saved_summary),
    }
