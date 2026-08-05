"""
企业AI智能考试与能力评估系统 - 后端入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.exceptions import AppException
from app.exceptions.handler import app_exception_handler

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

# ============================================================
# CORS 中间件
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:80",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 全局异常处理器
# ============================================================
app.add_exception_handler(AppException, app_exception_handler)

# ============================================================
# API 路由挂载
# 所有业务接口统一在 /api/v1 下
# ============================================================
app.include_router(api_router, prefix="/api")


# 根级健康检查
@app.get("/health")
async def root_health():
    return {"status": "ok", "version": settings.VERSION}