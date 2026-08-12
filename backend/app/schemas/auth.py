"""
认证 Schema
"""
import re
from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema


class LoginRequest(BaseSchema):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterRequest(BaseSchema):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=64)
    email: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=20)
    role: str = Field(default="employee", pattern="^(admin|employee|candidate|hr)$")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, v):
            raise ValueError("邮箱格式不正确")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^1[3-9]\d{9}$", cleaned):
            raise ValueError("手机号格式不正确")
        return cleaned


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
