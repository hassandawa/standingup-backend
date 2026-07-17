import logging
import secrets
from datetime import datetime, timezone
from bson import ObjectId, errors as bson_errors
from app.database import founder_profiles, startup_plans, saved_analyses, customer_strategies, decision_reports, business_plans, customer_insights, market_intelligence, ai_cofounder_chats, investor_tools, marketing_hub, development_hubs, growth_hubs, financial_plans, launch_hubs, teams, team_invites, team_analyses, comments, saved_ideas

logger = logging.getLogger(__name__)


def serialize_doc(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


def save_founder_profile(profile: dict) -> str:
    profile["created_at"] = datetime.now(timezone.utc)
    result = founder_profiles.insert_one(profile)
    return str(result.inserted_id)


def save_startup_plan(plan: dict, profile: dict, user_id: str | None = None) -> str:
    doc = {
        "plan": plan,
        "profile": profile,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = startup_plans.insert_one(doc)
    return str(result.inserted_id)


def get_saved_plans(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    plans = list(startup_plans.find(query).sort("created_at", -1))
    return [serialize_doc(p) for p in plans]


def save_idea_analysis(analysis: dict, idea_form: dict, user_id: str | None = None) -> str:
    doc = {
        "analysis": analysis,
        "idea_form": idea_form,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = saved_analyses.insert_one(doc)
    return str(result.inserted_id)


def get_saved_idea_analyses(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(saved_analyses.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def delete_saved_idea_analysis(analysis_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(analysis_id)
    except (bson_errors.InvalidId, TypeError):
        logger.warning("Invalid analysis_id format: %s", analysis_id)
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = saved_analyses.delete_one(query)
    return result.deleted_count > 0


def save_shared_analysis(analysis: dict, idea_form: dict) -> str:
    token = secrets.token_urlsafe(16)
    doc = {
        "token": token,
        "analysis": analysis,
        "idea_form": idea_form,
        "created_at": datetime.now(timezone.utc),
    }
    from app.database import shared_analyses
    shared_analyses.insert_one(doc)
    return token


def get_shared_analysis(token: str) -> dict | None:
    from app.database import shared_analyses
    doc = shared_analyses.find_one({"token": token})
    if doc:
        doc["_id"] = str(doc["_id"])
        doc["created_at"] = doc["created_at"].isoformat()
        return doc
    return None


def save_build_progress(token: str, day: int, completed_tasks: list[str], notes: str = "") -> dict:
    from app.database import build_progress
    doc = build_progress.find_one({"token": token})
    if not doc:
        doc = {"token": token, "days": {}, "created_at": datetime.now(timezone.utc)}
    if "days" not in doc:
        doc["days"] = {}
    doc["days"][str(day)] = {"completed_tasks": completed_tasks, "notes": notes, "updated_at": datetime.now(timezone.utc).isoformat()}
    build_progress.replace_one({"token": token}, doc, upsert=True)
    return {"days": doc["days"]}


def get_build_progress(token: str) -> dict | None:
    from app.database import build_progress
    doc = build_progress.find_one({"token": token})
    if doc:
        return {"days": doc.get("days", {})}
    return {"days": {}}


def track_event(event: str, properties: dict | None = None) -> None:
    from app.database import analytics_events
    analytics_events.insert_one({
        "event": event,
        "properties": properties or {},
        "created_at": datetime.now(timezone.utc),
    })


def get_analytics_summary() -> dict:
    from app.database import analytics_events, shared_analyses
    total_analyses = analytics_events.count_documents({"event": "idea_analysis"})
    total_shares = shared_analyses.count_documents({})
    total_chats = analytics_events.count_documents({"event": "idea_chat"})
    pipeline = [
        {"$match": {"event": "idea_analysis"}},
        {"$group": {"_id": "$properties.industry", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    top_industries = [{"industry": r["_id"] or "unknown", "count": r["count"]} for r in analytics_events.aggregate(pipeline)]
    recent = list(analytics_events.find().sort("created_at", -1).limit(20))
    recent_events = []
    for r in recent:
        recent_events.append({
            "event": r["event"],
            "properties": r.get("properties", {}),
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
        })
    return {
        "total_analyses": total_analyses,
        "total_shares": total_shares,
        "total_chats": total_chats,
        "top_industries": top_industries,
        "recent_events": recent_events,
    }


def delete_startup_plan(plan_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(plan_id)
    except (bson_errors.InvalidId, TypeError):
        logger.warning("Invalid plan_id format: %s", plan_id)
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = startup_plans.delete_one(query)
    return result.deleted_count > 0


def save_customer_strategy(strategy: dict, idea_context: dict, user_id: str | None = None) -> str:
    doc = {
        "strategy": strategy,
        "idea_context": idea_context,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = customer_strategies.insert_one(doc)
    return str(result.inserted_id)


def get_customer_strategies(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(customer_strategies.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def save_decision_report(report: dict, idea_context: dict, user_id: str | None = None) -> str:
    doc = {
        "report": report,
        "idea_context": idea_context,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = decision_reports.insert_one(doc)
    return str(result.inserted_id)


def get_decision_reports(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(decision_reports.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def delete_decision_report(report_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(report_id)
    except (bson_errors.InvalidId, TypeError):
        logger.warning("Invalid report_id format: %s", report_id)
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = decision_reports.delete_one(query)
    return result.deleted_count > 0


def save_business_plan(plan: dict, idea_context: dict, user_id: str | None = None) -> str:
    doc = {
        "plan": plan,
        "idea_context": idea_context,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = business_plans.insert_one(doc)
    return str(result.inserted_id)


def get_business_plans(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(business_plans.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def delete_business_plan(plan_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(plan_id)
    except (bson_errors.InvalidId, TypeError):
        logger.warning("Invalid plan_id format: %s", plan_id)
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = business_plans.delete_one(query)
    return result.deleted_count > 0


def save_customer_insights(insights: dict, idea_context: dict, user_id: str | None = None) -> str:
    doc = {
        "insights": insights,
        "idea_context": idea_context,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = customer_insights.insert_one(doc)
    return str(result.inserted_id)


def get_customer_insights_list(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(customer_insights.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def delete_customer_insights(insights_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(insights_id)
    except (bson_errors.InvalidId, TypeError):
        logger.warning("Invalid insights_id format: %s", insights_id)
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = customer_insights.delete_one(query)
    return result.deleted_count > 0


def delete_customer_strategy(strategy_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(strategy_id)
    except (bson_errors.InvalidId, TypeError):
        logger.warning("Invalid strategy_id format: %s", strategy_id)
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = customer_strategies.delete_one(query)
    return result.deleted_count > 0


def save_market_intelligence(report: dict, idea_context: dict, user_id: str | None = None) -> str:
    doc = {
        "report": report,
        "idea_context": idea_context,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = market_intelligence.insert_one(doc)
    return str(result.inserted_id)


def get_market_intelligence_list(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(market_intelligence.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def delete_market_intelligence(report_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(report_id)
    except (bson_errors.InvalidId, TypeError):
        logger.warning("Invalid report_id format: %s", report_id)
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = market_intelligence.delete_one(query)
    return result.deleted_count > 0


def save_ai_cofounder_chat(advisor_type: str, messages: list, user_id: str | None = None) -> str:
    doc = {
        "advisor_type": advisor_type,
        "messages": messages,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = ai_cofounder_chats.insert_one(doc)
    return str(result.inserted_id)


def get_ai_cofounder_chats(advisor_type: str, user_id: str | None = None, limit: int = 50) -> list:
    query = {"advisor_type": advisor_type}
    if user_id:
        query["user_id"] = user_id
    docs = list(ai_cofounder_chats.find(query).sort("created_at", -1).limit(limit))
    return [serialize_doc(d) for d in docs]


def delete_ai_cofounder_chat(chat_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(chat_id)
    except (bson_errors.InvalidId, TypeError):
        logger.warning("Invalid chat_id format: %s", chat_id)
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = ai_cofounder_chats.delete_one(query)
    return result.deleted_count > 0


def save_investor_tools(report: dict, idea_context: dict, user_id: str | None = None) -> str:
    doc = {
        "report": report,
        "idea_context": idea_context,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = investor_tools.insert_one(doc)
    return str(result.inserted_id)


def get_investor_tools_list(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(investor_tools.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def delete_investor_tools(report_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(report_id)
    except (bson_errors.InvalidId, TypeError):
        logger.warning("Invalid report_id format: %s", report_id)
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = investor_tools.delete_one(query)
    return result.deleted_count > 0


def save_marketing_hub(report: dict, idea_context: dict, user_id: str | None = None) -> str:
    doc = {
        "report": report,
        "idea_context": idea_context,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = marketing_hub.insert_one(doc)
    return str(result.inserted_id)


def get_marketing_hub_list(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(marketing_hub.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def delete_marketing_hub(report_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(report_id)
    except (bson_errors.InvalidId, TypeError):
        logger.warning("Invalid report_id format: %s", report_id)
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = marketing_hub.delete_one(query)
    return result.deleted_count > 0


# ─── Development Hub ──────────────────────────────────────────────────────────

def save_development_hub(report: dict, idea_context: dict, user_id: str | None = None) -> str:
    doc = {
        "report": report,
        "idea_context": idea_context,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = development_hubs.insert_one(doc)
    return str(result.inserted_id)


def get_development_hub_list(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(development_hubs.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def delete_development_hub(report_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(report_id)
    except (bson_errors.InvalidId, TypeError):
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = development_hubs.delete_one(query)
    return result.deleted_count > 0


# ─── Growth Hub ───────────────────────────────────────────────────────────────

def save_growth_hub(report: dict, idea_context: dict, user_id: str | None = None) -> str:
    doc = {
        "report": report,
        "idea_context": idea_context,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = growth_hubs.insert_one(doc)
    return str(result.inserted_id)


def get_growth_hub_list(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(growth_hubs.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def delete_growth_hub(report_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(report_id)
    except (bson_errors.InvalidId, TypeError):
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = growth_hubs.delete_one(query)
    return result.deleted_count > 0


# ─── Financial Planning Hub ───────────────────────────────────────────────────

def save_financial_plan(report: dict, idea_context: dict, user_id: str | None = None) -> str:
    doc = {
        "report": report,
        "idea_context": idea_context,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = financial_plans.insert_one(doc)
    return str(result.inserted_id)


def get_financial_plan_list(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(financial_plans.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def delete_financial_plan(report_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(report_id)
    except (bson_errors.InvalidId, TypeError):
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = financial_plans.delete_one(query)
    return result.deleted_count > 0


# ─── Launch Hub ───────────────────────────────────────────────────────────────

def save_launch_hub(report: dict, checked_items: list[str] | None = None, idea_context: dict | None = None, user_id: str | None = None) -> str:
    doc = {
        "report": report,
        "checked_items": checked_items or [],
        "idea_context": idea_context or {},
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = launch_hubs.insert_one(doc)
    return str(result.inserted_id)


def get_launch_hub_list(user_id: str | None = None) -> list:
    query = {"user_id": user_id} if user_id else {}
    docs = list(launch_hubs.find(query).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


def update_launch_hub_checks(report_id: str, checked_items: list[str], user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(report_id)
    except (bson_errors.InvalidId, TypeError):
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = launch_hubs.update_one(query, {"$set": {"checked_items": checked_items}})
    return result.modified_count > 0


def delete_launch_hub(report_id: str, user_id: str | None = None) -> bool:
    try:
        obj_id = ObjectId(report_id)
    except (bson_errors.InvalidId, TypeError):
        return False
    query = {"_id": obj_id}
    if user_id:
        query["user_id"] = user_id
    result = launch_hubs.delete_one(query)
    return result.deleted_count > 0


# ─── Teams ────────────────────────────────────────────────────────────────────

def create_team(name: str, description: str, owner_id: str, owner_email: str, owner_name: str) -> dict:
    invite_code = secrets.token_urlsafe(8)
    doc = {
        "name": name,
        "description": description,
        "owner_id": owner_id,
        "invite_code": invite_code,
        "members": [{"user_id": owner_id, "email": owner_email, "name": owner_name, "role": "owner", "joined_at": datetime.now(timezone.utc).isoformat()}],
        "created_at": datetime.now(timezone.utc),
    }
    result = teams.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    doc["id"] = str(result.inserted_id)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc


def get_user_teams(user_id: str) -> list:
    docs = list(teams.find({"members.user_id": user_id}).sort("created_at", -1))
    for d in docs:
        d["_id"] = str(d["_id"])
        d["id"] = str(d["_id"])
        d["created_at"] = d.get("created_at", datetime.now(timezone.utc)).isoformat() if hasattr(d.get("created_at"), "isoformat") else str(d.get("created_at", ""))
    return docs


def get_team_by_invite_code(code: str) -> dict | None:
    doc = teams.find_one({"invite_code": code})
    if doc:
        doc["_id"] = str(doc["_id"])
        doc["id"] = str(doc["_id"])
        doc["created_at"] = doc["created_at"].isoformat() if hasattr(doc["created_at"], "isoformat") else str(doc["created_at"])
        return doc
    return None


def join_team(invite_code: str, user_id: str, email: str, name: str) -> dict | None:
    team = teams.find_one({"invite_code": invite_code})
    if not team:
        return None
    already_member = any(m.get("user_id") == user_id for m in team.get("members", []))
    if already_member:
        return {"_id": str(team["_id"]), "already_member": True}
    new_member = {"user_id": user_id, "email": email, "name": name, "role": "viewer", "joined_at": datetime.now(timezone.utc).isoformat()}
    teams.update_one({"_id": team["_id"]}, {"$push": {"members": new_member}})
    team["members"].append(new_member)
    team["_id"] = str(team["_id"])
    team["id"] = str(team["_id"])
    team["created_at"] = team["created_at"].isoformat() if hasattr(team["created_at"], "isoformat") else str(team["created_at"])
    return team


def add_team_analysis(team_id: str, report_type: str, report_id: str, title: str, added_by: str) -> str:
    try:
        obj_id = ObjectId(team_id)
    except (bson_errors.InvalidId, TypeError):
        return ""
    doc = {
        "team_id": team_id,
        "report_type": report_type,
        "report_id": report_id,
        "title": title,
        "added_by": added_by,
        "created_at": datetime.now(timezone.utc),
    }
    result = team_analyses.insert_one(doc)
    return str(result.inserted_id)


def get_team_analyses(team_id: str) -> list:
    docs = list(team_analyses.find({"team_id": team_id}).sort("created_at", -1))
    return [serialize_doc(d) for d in docs]


# ─── Comments ─────────────────────────────────────────────────────────────────

def create_comment(target_type: str, target_id: str, section: str, text: str, user_id: str, user_name: str) -> dict:
    doc = {
        "target_type": target_type,
        "target_id": target_id,
        "section": section,
        "text": text,
        "user_id": user_id,
        "user_name": user_name,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = comments.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    doc["id"] = str(result.inserted_id)
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    return doc


def get_comments(target_type: str, target_id: str) -> list:
    docs = list(comments.find({"target_type": target_type, "target_id": target_id}).sort("created_at", 1))
    for d in docs:
        d["_id"] = str(d["_id"])
        d["id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else str(d["created_at"])
        d["updated_at"] = d["updated_at"].isoformat() if hasattr(d["updated_at"], "isoformat") else str(d["updated_at"])
    return docs


def delete_comment(comment_id: str, user_id: str) -> bool:
    try:
        obj_id = ObjectId(comment_id)
    except (bson_errors.InvalidId, TypeError):
        return False
    result = comments.delete_one({"_id": obj_id, "user_id": user_id})
    return result.deleted_count > 0


# ─── Saved Ideas (Centralized Idea Registry) ──────────────────────────────────

def save_saved_idea(user_id: str, title: str, description: str, idea_data: dict, analysis: dict, plan: dict, profile: dict) -> str:
    doc = {
        "user_id": user_id,
        "title": title,
        "description": description,
        "idea_data": idea_data,
        "analysis": analysis,
        "plan": plan,
        "profile": profile,
        "hub_reports": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = saved_ideas.insert_one(doc)
    return str(result.inserted_id)


def get_saved_ideas(user_id: str) -> list:
    docs = list(saved_ideas.find({"user_id": user_id}).sort("created_at", -1))
    for d in docs:
        d["_id"] = str(d["_id"])
        d["id"] = str(d["_id"])
        d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else str(d["created_at"])
        d["updated_at"] = d["updated_at"].isoformat() if hasattr(d["updated_at"], "isoformat") else str(d["updated_at"])
    return docs


def get_saved_idea(idea_id: str, user_id: str) -> dict | None:
    try:
        obj_id = ObjectId(idea_id)
    except (bson_errors.InvalidId, TypeError):
        return None
    doc = saved_ideas.find_one({"_id": obj_id, "user_id": user_id})
    if not doc:
        return None
    doc["_id"] = str(doc["_id"])
    doc["id"] = str(doc["_id"])
    doc["created_at"] = doc["created_at"].isoformat() if hasattr(doc["created_at"], "isoformat") else str(doc["created_at"])
    doc["updated_at"] = doc["updated_at"].isoformat() if hasattr(doc["updated_at"], "isoformat") else str(doc["updated_at"])
    return doc


def update_saved_idea(idea_id: str, user_id: str, updates: dict) -> bool:
    try:
        obj_id = ObjectId(idea_id)
    except (bson_errors.InvalidId, TypeError):
        return False
    updates["updated_at"] = datetime.now(timezone.utc)
    result = saved_ideas.update_one({"_id": obj_id, "user_id": user_id}, {"$set": updates})
    return result.modified_count > 0


def update_saved_idea_hub_reports(idea_id: str, user_id: str, hub_key: str, report_data: dict) -> bool:
    try:
        obj_id = ObjectId(idea_id)
    except (bson_errors.InvalidId, TypeError):
        return False
    result = saved_ideas.update_one(
        {"_id": obj_id, "user_id": user_id},
        {"$set": {f"hub_reports.{hub_key}": report_data, "updated_at": datetime.now(timezone.utc)}}
    )
    return result.modified_count > 0


def delete_saved_idea(idea_id: str, user_id: str) -> bool:
    try:
        obj_id = ObjectId(idea_id)
    except (bson_errors.InvalidId, TypeError):
        return False
    result = saved_ideas.delete_one({"_id": obj_id, "user_id": user_id})
    return result.deleted_count > 0
