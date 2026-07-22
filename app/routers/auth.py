"""
app/routers/auth.py
POST /auth/register — register a new user
POST /auth/login    — login and get JWT token
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.core.database import get_db
from app.core.auth import hash_password, verify_password, create_access_token
from app.models.models import User
from app.schemas.schemas import UserCreate, UserResponse
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post(
    "/register",
    response_model=UserResponse,
    summary="Register a new user",
    description="""
## Register
Creates a new trader account in the system.

**Request body:**
- `username` — unique username
- `email` — unique email address
- `password` — plain text password (hashed with bcrypt before storage)

**Responses:**
- `200` — User created successfully
- `400` — Username or email already taken

**No authentication required.**
    """
)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT token",
    description="""
## Login
Authenticates a trader and returns a JWT bearer token.

**Request body (form-data):**
- `username` — registered username
- `password` — account password

**Responses:**
- `200` — Returns JWT access token (valid 30 minutes)
- `401` — Incorrect username or password

**No authentication required.**
    """
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    token = create_access_token(data={"sub": user.username, "mode": user.mode or "COPILOT"})
    return {"access_token": token, "token_type": "bearer"}