from typing import Optional
from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    system_mode: Optional[str] = "copilot"
