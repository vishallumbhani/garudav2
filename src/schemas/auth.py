"""
src/schemas/auth.py
Pydantic schemas for JWT authentication.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role: str
    tenant_id: Optional[str] = None
    enabled: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    role: str = "viewer"  # admin | operator | viewer | auditor
    tenant_id: Optional[str] = "default"


class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    tenant_id: Optional[str] = None
    enabled: Optional[bool] = None


class PasswordReset(BaseModel):
    new_password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str
