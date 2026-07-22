from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User

router = APIRouter(prefix="/admin", tags=["Admin"])

class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/users", response_model=List[AdminUserResponse], summary="Get all registered users (admin only)")
def get_all_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin role required.")
    users = db.query(User).all()
    return users
