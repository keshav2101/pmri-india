"""schemas/auth.py — Auth schemas for PMRI India."""
from pydantic import BaseModel, EmailStr
from typing import Optional

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    account_type: str = "RETAIL"   # "RETAIL" | "INSTITUTIONAL"
    org_name: Optional[str] = None  # required if account_type == INSTITUTIONAL

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    tier: str
    is_admin: bool

class UserResponse(BaseModel):
    id: str
    email: str
    tier: str
    is_admin: bool
    created_at: str

    class Config:
        from_attributes = True
