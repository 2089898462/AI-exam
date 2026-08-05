"""
认证 Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema


class LoginRequest(BaseSchema):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterRequest(BaseSchema):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=64)
    email: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=20)
    role: str = Field(default="candidate", pattern="^(admin|candidate|hr)$")


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: dict


class CurrentUserResponse(BaseSchema):
    id: int
    username: str
    display_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
