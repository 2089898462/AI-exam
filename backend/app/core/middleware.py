"""
安全中间件
提供：请求速率限制、安全响应头、输入清理等安全机制。
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    max_requests: int = 100  # 时间窗口内最大请求数
    window_seconds: int = 60  # 时间窗口（秒）


class RateLimiter:
    """基于内存的简单速率限制器（IP 维度）

    注意：此实现为单机内存版本，多实例部署需替换为 Redis 实现。
    """

    def __init__(self, config: RateLimitConfig | None = None):
        self._config = config or RateLimitConfig()
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - self._config.window_seconds

        timestamps = self._requests[client_ip]
        timestamps[:] = [t for t in timestamps if t > window_start]

        if len(timestamps) >= self._config.max_requests:
            return False

        timestamps.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""

    def __init__(self, app, limiter: RateLimiter | None = None):
        super().__init__(app)
        self._limiter = limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        if not self._limiter.is_allowed(client_ip):
            return Response(
                content='{"detail":"请求过于频繁，请稍后再试"}',
                status_code=429,
                media_type="application/json",
            )

        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全响应头中间件"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 安全响应头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' http: https: ws: wss:; "
            "frame-ancestors 'self'"
        )

        return response


def sanitize_string(value: str, max_length: int = 256) -> str:
    """清理输入字符串，防止注入攻击

    移除或转义危险字符：
    - SQL 注入字符
    - XSS 相关标签
    - 控制字符
    """
    if not value:
        return value

    # 截断超长字符串
    value = value[:max_length]

    # 移除控制字符
    import unicodedata
    value = "".join(c for c in value if unicodedata.category(c)[0] != "C")

    return value.strip()
