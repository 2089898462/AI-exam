"""
AI 智能评分与报告生成服务 - 入口

安全说明：
- AI-Service 为内部服务，仅接受 Backend 调用
- 生产环境应部署在内部网络，不对外暴露
- API Key 必须通过环境变量配置
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import router as api_router
from app.core.config import validate_ai_config
from app.core.logger import get_logger, setup_logging
from app.tools.tool_registry import get_tool_registry
from app.tools.exam_tools import register_exam_tools

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # AI 服务启动安全检查
    warnings = validate_ai_config()
    for w in warnings:
        logger.warning(w)

    if warnings:
        logger.warning(
            "[SECURITY] AI-Service 存在安全配置警告，请检查 AI_API_KEY 设置。"
        )

    # 注册 AI Agent 工具
    registry = get_tool_registry()
    register_exam_tools(registry)
    logger.info(f"AI Agent 工具注册完成: {len(registry.get_all_tools())} 个工具")

    yield


app = FastAPI(title="AI 评分服务", version="0.1.0", lifespan=lifespan)

# CORS - 限制为仅 Backend 内部调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# AI-Service 全局异常处理
@app.exception_handler(Exception)
async def ai_service_exception_handler(request: Request, exc: Exception):
    """AI-Service 异常处理 - 不泄露内部细节"""
    logger.error(
        f"AI-Service 异常: {type(exc).__name__}: {str(exc)}", exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "AI 服务暂时不可用，请稍后重试",
            "data": None,
        },
    )


app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai-scoring"}
