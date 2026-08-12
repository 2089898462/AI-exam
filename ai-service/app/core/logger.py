"""
AI-Service 统一日志配置模块

专为 AI 服务设计，增加：
- AI 请求记录
- 模型调用日志
- Prompt 版本追踪
- 耗时统计
- 异常堆栈记录
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
import time
from pathlib import Path
from typing import Optional

# 日志目录
LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志文件
LOG_FILE = LOG_DIR / "ai_service.log"
LOG_AI_FILE = LOG_DIR / "ai_calls.log"
LOG_ERROR_FILE = LOG_DIR / "ai_service_error.log"

# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# AI 专用日志格式
AI_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"


def setup_logging(level: Optional[str] = None) -> None:
    """初始化日志配置

    生产环境自动降级为 INFO，开发环境使用 DEBUG。
    可通过环境变量 LOG_LEVEL 显式指定。
    """
    import os
    env_level = os.environ.get("LOG_LEVEL", "")
    log_level = level or env_level or "INFO"

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.DEBUG))

    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level, logging.DEBUG))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件输出（全量）
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(LOG_FILE),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 错误日志
    error_handler = logging.handlers.RotatingFileHandler(
        filename=str(LOG_ERROR_FILE),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)


def get_logger(name: str) -> logging.Logger:
    """获取模块级 logger"""
    return logging.getLogger(name)


# --- AI 专用日志工具 ---

_ai_logger: Optional[logging.Logger] = None


def _get_ai_logger() -> logging.Logger:
    global _ai_logger
    if _ai_logger is None:
        _ai_logger = logging.getLogger("ai_calls")
        _ai_logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(AI_LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

        handler = logging.handlers.RotatingFileHandler(
            filename=str(LOG_AI_FILE),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        _ai_logger.addHandler(handler)

    return _ai_logger


def log_ai_request(
    endpoint: str,
    model: str,
    prompt_version: str,
    input_size: int = 0,
) -> None:
    """记录 AI 请求（不记录敏感内容）

    Args:
        endpoint: API 端点
        model: 使用的模型
        prompt_version: Prompt 版本
        input_size: 输入大小（字符数）
    """
    logger = _get_ai_logger()
    logger.info(
        f"[AI_REQUEST] endpoint={endpoint} | model={model} | "
        f"prompt_version={prompt_version} | input_size={input_size}"
    )


def log_ai_response(
    endpoint: str,
    status: str,
    latency_ms: float,
    output_size: int = 0,
) -> None:
    """记录 AI 响应

    Args:
        endpoint: API 端点
        status: 状态（success/error）
        latency_ms: 耗时（毫秒）
        output_size: 输出大小（字符数）
    """
    logger = _get_ai_logger()
    logger.info(
        f"[AI_RESPONSE] endpoint={endpoint} | status={status} | "
        f"latency_ms={latency_ms:.1f} | output_size={output_size}"
    )


def log_ai_error(
    endpoint: str,
    error_type: str,
    error_msg: str,
    latency_ms: float,
) -> None:
    """记录 AI 异常

    Args:
        endpoint: API 端点
        error_type: 错误类型
        error_msg: 错误信息（已脱敏）
        latency_ms: 耗时（毫秒）
    """
    logger = _get_ai_logger()
    logger.error(
        f"[AI_ERROR] endpoint={endpoint} | error_type={error_type} | "
        f"latency_ms={latency_ms:.1f} | {error_msg[:200]}"
    )


class Timer:
    """耗时计时器，用于 AI 调用计时"""

    def __init__(self) -> None:
        self._start: float = 0
        self._end: float = 0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self._end = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        """耗时（毫秒）"""
        return (self._end - self._start) * 1000.0
