import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import create_jwt_token, get_current_user
from app.core.websocket import manager
from app.models.user import UserModel
from app.models.state import SystemStateModel
from app.schemas.auth import RegisterRequest, LoginRequest
from app.schemas.trade import ModeRequest

router = APIRouter(tags=["Authentication & Users"])

@router.post("/auth/register")
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )
    
    display_name = payload.username or payload.name or email.split("@")[0]
    new_user = UserModel(
        id=str(uuid.uuid4()),
        name=display_name,
        email=email,
        password=payload.password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_jwt_token({"sub": new_user.email, "id": new_user.id})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600,
        samesite="lax",
        secure=False
    )
    
    state = db.query(SystemStateModel).filter(SystemStateModel.key == "mode").first()
    system_mode = state.value if state else "copilot"
    
    return {
        "id": new_user.id,
        "name": new_user.name,
        "username": new_user.name,
        "email": new_user.email,
        "token": token,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email
        },
        "system_mode": system_mode,
        "mode": system_mode.upper(),
        "is_broker_connected": True
    }

@router.post("/auth/login")
async def login(request: Request, response: Response, db: Session = Depends(get_db)):
    identifier = None
    password = None
    
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            identifier = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            identifier = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            pass
            
    if not identifier or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier (email/username) and password are required"
        )
        
    ident_clean = str(identifier).strip()
    user = db.query(UserModel).filter(
        or_(
            UserModel.email == ident_clean.lower(),
            UserModel.name == ident_clean
        )
    ).first()
    
    if not user or user.password != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    token = create_jwt_token({"sub": user.email, "id": user.id})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600,
        samesite="lax",
        secure=False
    )
    
    state = db.query(SystemStateModel).filter(SystemStateModel.key == "mode").first()
    system_mode = state.value if state else "copilot"
    
    return {
        "id": user.id,
        "name": user.name,
        "username": user.name,
        "email": user.email,
        "token": token,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        },
        "system_mode": system_mode,
        "mode": system_mode.upper(),
        "is_broker_connected": True
    }

@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/auth/me")
def get_me(user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    state = db.query(SystemStateModel).filter(SystemStateModel.key == "mode").first()
    system_mode = state.value if state else "copilot"
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "username": user.name,
            "email": user.email
        },
        "id": user.id,
        "name": user.name,
        "username": user.name,
        "email": user.email,
        "isAuthenticated": True,
        "isBrokerConnected": True,
        "systemMode": system_mode,
        "mode": system_mode.upper()
    }

@router.get("/user/me")
def get_user_profile(user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    state = db.query(SystemStateModel).filter(SystemStateModel.key == "mode").first()
    system_mode = state.value if state else "copilot"
    return {
        "id": user.id,
        "name": user.name,
        "username": user.name,
        "email": user.email,
        "system_mode": system_mode,
        "mode": system_mode.upper()
    }

@router.get("/user/mode")
def get_user_mode(db: Session = Depends(get_db)):
    state = db.query(SystemStateModel).filter(SystemStateModel.key == "mode").first()
    mode = state.value if state else "copilot"
    return {"mode": mode.upper(), "system_mode": mode.lower()}

@router.patch("/user/mode")
async def update_user_mode(payload: ModeRequest, db: Session = Depends(get_db)):
    mode = payload.mode.lower()
    if mode not in ["copilot", "autopilot"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be 'copilot' or 'autopilot'"
        )
    state = db.query(SystemStateModel).filter(SystemStateModel.key == "mode").first()
    if not state:
        state = SystemStateModel(key="mode", value=mode)
        db.add(state)
    else:
        state.value = mode
    db.commit()
    await manager.publish({"event": "mode_updated", "mode": mode})
    return {"status": "success", "mode": mode.upper(), "system_mode": mode.lower()}
