import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from app.models.schemas import SavedIdeaCreate, SavedIdeaUpdate
from app.services.auth_service import get_user_by_token
from app.services.database_service import (
    save_saved_idea,
    get_saved_ideas,
    get_saved_idea,
    update_saved_idea,
    update_saved_idea_hub_reports,
    delete_saved_idea,
)
from app.services.database_service import track_event

logger = logging.getLogger(__name__)

router = APIRouter()


def _optional_user_id(authorization: str = Header(default="")) -> str | None:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    user = get_user_by_token(token)
    return user["id"] if user else None


def _require_user_id(authorization: str = Header(default="")) -> str:
    user_id = _optional_user_id(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in required.")
    return user_id


@router.get("/api/saved-ideas")
async def list_saved_ideas(user_id: str = Depends(_require_user_id)):
    try:
        ideas = get_saved_ideas(user_id=user_id)
        return {"ideas": ideas}
    except Exception as e:
        logger.error("List saved ideas failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch saved ideas.")


@router.post("/api/saved-ideas")
async def create_saved_idea(body: dict, user_id: str = Depends(_require_user_id)):
    try:
        track_event("save_idea", {"user_id": user_id})
        title = body.get("title", "")
        description = body.get("description", "")
        idea_data = body.get("idea_data", {})
        analysis = body.get("analysis", {})
        plan = body.get("plan", {})
        profile = body.get("profile", {})
        if not title:
            raise HTTPException(status_code=400, detail="Title is required.")
        idea_id = save_saved_idea(
            user_id=user_id,
            title=title,
            description=description,
            idea_data=idea_data,
            analysis=analysis,
            plan=plan,
            profile=profile,
        )
        return {"idea_id": idea_id, "message": "Idea saved successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Save idea failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save idea.")


@router.get("/api/saved-ideas/{idea_id}")
async def get_saved_idea_detail(idea_id: str, user_id: str = Depends(_require_user_id)):
    try:
        idea = get_saved_idea(idea_id, user_id=user_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found.")
        return idea
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get saved idea failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch idea.")


@router.put("/api/saved-ideas/{idea_id}")
async def update_saved_idea_endpoint(idea_id: str, body: dict, user_id: str = Depends(_require_user_id)):
    try:
        updates = {}
        for key in ("title", "description", "idea_data", "analysis", "plan", "profile", "hub_reports"):
            if key in body:
                updates[key] = body[key]
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update.")
        updated = update_saved_idea(idea_id, user_id=user_id, updates=updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Idea not found.")
        return {"message": "Idea updated successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update idea failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update idea.")


@router.patch("/api/saved-ideas/{idea_id}/hub-reports")
async def update_hub_reports(idea_id: str, body: dict, user_id: str = Depends(_require_user_id)):
    try:
        hub_key = body.get("hub_key", "")
        report_data = body.get("report_data", {})
        if not hub_key:
            raise HTTPException(status_code=400, detail="hub_key is required.")
        updated = update_saved_idea_hub_reports(idea_id, user_id=user_id, hub_key=hub_key, report_data=report_data)
        if not updated:
            raise HTTPException(status_code=404, detail="Idea not found.")
        return {"message": "Hub report linked successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update hub reports failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update hub reports.")


@router.delete("/api/saved-ideas/{idea_id}")
async def delete_saved_idea_endpoint(idea_id: str, user_id: str = Depends(_require_user_id)):
    try:
        deleted = delete_saved_idea(idea_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Idea not found.")
        return {"message": "Idea deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Delete idea failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete idea.")
