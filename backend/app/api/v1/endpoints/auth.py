"""
认证端点
POST /auth/login  - 登录
POST /auth/register - 注册（开放）
GET  /auth/me     - 获取当前用户
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import AuthService
from app.utils.response import ApiResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    """账号密码登录，返回 JWT Token"""
    service = AuthService(db)
    result = service.login(data.username, data.password)
    return ApiResponse.success(data=result)


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """注册新用户并自动登录"""
    service = AuthService(db)
    user = service.register(
        username=data.username,
        password=data.password,
        display_name=data.display_name,
        email=data.email,
        phone=data.phone,
        role=data.role,
    )
    result = service.login(user.username, data.password)
    return ApiResponse.created(data=result)


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    data = CurrentUserResponse.model_validate(current_user).model_dump()
    return ApiResponse.success(data=data)


@router.post("/logout")
async def logout():
    """登出（客户端删除 Token 即可，此处仅做占位）"""
    return ApiResponse.success(message="登出成功")
