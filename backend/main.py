"""
AI考试系统（企业内部版）- 后端入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import settings
from app.core.data_masking import register_data_masking
from app.core.logger import get_logger, setup_logging
from app.core.middleware import (
    RateLimitConfig,
    RateLimitMiddleware,
    RateLimiter,
    SecurityHeadersMiddleware,
)
from app.core.request_logging import (
    get_request_id,
    get_trace_id,
    register_request_logging,
)
from app.core.security_check import check_production_safety, validate_security_config
from app.exceptions import AppException
from app.exceptions.handler import app_exception_handler

logger = get_logger(__name__)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)


@app.on_event("startup")
async def on_startup():
    setup_logging()

    sec_warnings = validate_security_config()
    prod_warnings = check_production_safety()

    for w in sec_warnings + prod_warnings:
        logger.warning(w)

    if sec_warnings:
        logger.warning(
            "[SECURITY] 存在安全配置警告，请检查 .env 文件设置。"
            "应用将继续运行，但请尽快修复。"
        )

# ============================================================
# CORS 中间件（必须最先添加，确保在响应阶段最后处理）
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ============================================================
# 请求日志 + 链路追踪中间件（装饰器模式，兼容 TestClient）
# ============================================================
register_request_logging(app)

# ============================================================
# 数据脱敏中间件（自动处理 PII 字段）
# ============================================================
register_data_masking(
    app,
    enabled=True,
    exclude_paths=["/docs", "/redoc", "/openapi.json", "/health"],
)

# ============================================================
# 安全中间件
# ============================================================
app.add_middleware(
    RateLimitMiddleware,
    limiter=RateLimiter(RateLimitConfig(max_requests=200, window_seconds=60)),
)
app.add_middleware(SecurityHeadersMiddleware)

# ============================================================
# 异常处理器
# ============================================================
app.add_exception_handler(AppException, app_exception_handler)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """全局异常处理器

    生产环境不返回堆栈信息，返回统一格式（含 trace_id + request_id）。
    """
    request_id = get_request_id(request)
    trace_id = get_trace_id(request)

    logger.error(
        f"[UNHANDLED_ERROR] trace_id={trace_id} | id={request_id} | "
        f"{request.method} {request.url.path} | "
        f"error={type(exc).__name__}: {str(exc)[:300]}",
        exc_info=True,
    )

    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"服务器内部错误: {str(exc)}",
                "data": None,
                "request_id": request_id,
                "trace_id": trace_id,
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "data": None,
            "request_id": request_id,
            "trace_id": trace_id,
        },
    )


# ============================================================
# API 路由挂载
# ============================================================
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def root_health():
    return {"status": "ok", "version": settings.VERSION}