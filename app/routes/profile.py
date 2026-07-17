import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import UserProfile, FounderProfileResponse
from app.services.ai_service import analyze_profile
from app.services.ai_errors import AIServiceError, AIRateLimitError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/profile/analyze", response_model=FounderProfileResponse)
async def analyze_user_profile(profile: UserProfile):
    try:
        result = await analyze_profile(profile.model_dump())
    except AIRateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limited. Please try again in a moment.")
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")
    except Exception as e:
        logger.error("Profile analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze profile. Please try again.")

    # Validate response has required fields
    required = ("founder_type", "strengths", "weaknesses", "best_startup_categories")
    missing = [f for f in required if f not in result]
    if missing:
        logger.error("Profile analysis missing fields: %s", missing)
        raise HTTPException(status_code=502, detail="AI returned an incomplete response. Please try again.")

    try:
        return FounderProfileResponse(**result)
    except Exception as e:
        logger.error("Profile response validation failed: %s", e)
        raise HTTPException(status_code=502, detail="AI returned an invalid response format.")
