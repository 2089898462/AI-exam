"""
AI 服务 API 路由注册

注册所有 AI 服务端点。
"""
from fastapi import APIRouter

from app.api.endpoints.agent import router as agent_router
from app.api.endpoints.health import router as health_router
from app.api.endpoints.report import router as report_router
from app.api.endpoints.scoring import router as scoring_router

router = APIRouter()


# 注册健康检查路由（包含 AI 配置检查和连接测试）
router.include_router(health_router, prefix="/health", tags=["健康检查"])

# 注册评分路由
router.include_router(scoring_router, prefix="/scoring", tags=["AI 评分"])

# 注册报告生成路由
router.include_router(report_router, prefix="/report", tags=["AI 报告"])

# 注册 AI Agent 路由
router.include_router(agent_router, prefix="/agent", tags=["AI Agent"])
