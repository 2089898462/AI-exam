"""
API 请求日志 + 链路追踪中间件

使用装饰器模式注册到 FastAPI app，避免 BaseHTTPMiddleware 的兼容性问题。

记录内容：
- trace_id（链路追踪 ID）
- request_id（请求 ID）
- 请求路径 + 方法
- 响应状态码
- 请求耗时
- 客户端 IP

禁止记录：
- 请求体（可能包含密码/答案）
- 完整 Authorization Token
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import FastAPI, Request, Response

from app.core.logger import get_logger
from app.core.trace import generate_request_id, generate_trace_id

logger = get_logger(__name__)

_SENSITIVE_PATHS = ("/auth/login", "/auth/register")


def register_request_logging(app: FastAPI) -> None:
    """注册请求日志 + 链路追踪中间件到 FastAPI 应用"""

    @app.middleware("http")
    async def request_logger_middleware(
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        trace_id = generate_trace_id()
        request_id = generate_request_id()

        request.state.trace_id = trace_id
        request.state.request_id = request_id

        client_ip = request.client.host if request.client else "unknown"
        start_time = time.perf_counter()

        # 健康检查路径不记录
        if request.url.path == "/health":
            return await call_next(request)

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[REQ_ERROR] trace_id={trace_id} | id={request_id} | "
                f"{request.method} {request.url.path} | "
                f"ip={client_ip} | elapsed_ms={elapsed:.1f} | "
                f"error={type(exc).__name__}: {str(exc)[:200]}"
            )
            raise

        elapsed = (time.perf_counter() - start_time) * 1000
        status_code = response.status_code

        # 日志等级根据状态码
        if status_code >= 500:
            log_fn = logger.error
        elif status_code >= 400:
            log_fn = logger.warning
        else:
            log_fn = logger.info

        # 安全过滤：敏感路径标记
        sensitive = any(p in request.url.path for p in _SENSITIVE_PATHS)
        sensitive_note = " | [SENSITIVE]" if sensitive else ""

        log_fn(
            f"[REQ] trace_id={trace_id} | id={request_id} | "
            f"{request.method} {request.url.path} | "
            f"status={status_code} | elapsed_ms={elapsed:.1f} | "
            f"ip={client_ip}{sensitive_note}"
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        return response


def get_request_id(request: Request) -> str:
    """从请求中获取 request_id"""
    return getattr(request.state, "request_id", "unknown")


def get_trace_id(request: Request) -> str:
    """从请求中获取 trace_id"""
    return getattr(request.state, "trace_id", "unknown")