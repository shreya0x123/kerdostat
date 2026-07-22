from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User
from app.schemas.schemas import UserResponse, UserModeUpdate

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    GET /user/me
    Returns the currently authenticated user's profile including operational mode.
    Requires valid JWT token.
    """
    return current_user


@router.patch("/mode", response_model=UserResponse, summary="Toggle user trading mode (COPILOT vs AUTOPILOT)")
def update_user_mode(
    mode_update: UserModeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    PATCH /user/mode
    Updates current user's mode to COPILOT (HITL) or AUTOPILOT (HOTL).
    Persists mode in PostgreSQL and returns updated user profile.
    Requires valid JWT token.
    """
    current_user.mode = mode_update.mode
    db.commit()
    db.refresh(current_user)
    return current_user