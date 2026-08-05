"""
健康检查端点
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.utils.response import ApiResponse

router = APIRouter()


@router.get("")
async def health_check():
    """基础健康检查（无需数据库）"""
    return ApiResponse.success(data={
        "status": "ok",
        "version": settings.VERSION,
    })


@router.get("/db")
async def db_health_check(db: Session = Depends(get_db)):
    """数据库健康检查"""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return ApiResponse.success(data={
        "status": "ok",
        "version": settings.VERSION,
        "database": db_status,
    })