"""
AI 服务 API 路由
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai-scoring"}
