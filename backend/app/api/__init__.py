"""
API 路由聚合入口
支持多版本路由挂载，当前版本 v1
"""
from fastapi import APIRouter

from app.api.v1 import v1_router

api_router = APIRouter()
api_router.include_router(v1_router, prefix="/v1")