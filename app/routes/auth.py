import logging

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import AuthResponse, ForgotPasswordRequest, SignInRequest, SignUpRequest, UserResponse
from app.services.auth_service import (
    AuthError,
    DuplicateUserError,
    authenticate_user,
    create_user,
    get_user_by_token,
    logout_user,
    request_password_reset,
    verify_reset_token,
    reset_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignUpRequest):
    try:
        return create_user(payload.name, payload.email, payload.password)
    except DuplicateUserError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Signup failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create account. Please try again.")


@router.post("/signin", response_model=AuthResponse)
def signin(payload: SignInRequest):
    try:
        return authenticate_user(payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        logger.error("Signin failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to sign in. Please try again.")


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    try:
        request_password_reset(payload.email)
    except AuthError:
        pass
    except Exception as exc:
        logger.error("Password reset request failed: %s", exc, exc_info=True)
    return {
        "message": "If an account exists with this email, password reset instructions have been sent.",
    }


@router.post("/verify-reset-token")
def verify_reset_token_endpoint(body: dict):
    token = body.get("token", "")
    if not token:
        raise HTTPException(status_code=400, detail="Reset token is required.")
    try:
        verify_reset_token(token)
        return {"message": "Token is valid."}
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Token verification failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify token.")


@router.post("/reset-password")
def reset_password_endpoint(body: dict):
    token = body.get("token", "")
    new_password = body.get("new_password", "")
    if not token:
        raise HTTPException(status_code=400, detail="Reset token is required.")
    if not new_password:
        raise HTTPException(status_code=400, detail="New password is required.")
    try:
        reset_password(token, new_password)
        return {"message": "Password has been reset successfully. You can now sign in with your new password."}
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Password reset failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reset password. Please try again.")


@router.get("/me", response_model=UserResponse)
def me(authorization: str = Header(default="")):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Missing auth token.")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid auth token.")
    return user


@router.post("/logout")
def logout(authorization: str = Header(default="")):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Missing auth token.")
    logout_user(token)
    return {"message": "Signed out successfully"}
