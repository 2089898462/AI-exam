"""
AI 智能评分与报告生成服务 - 入口
"""
from fastapi import FastAPI

from app.api.router import router as api_router

app = FastAPI(title="AI 评分服务", version="0.1.0")

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai-scoring"}
