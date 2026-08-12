"""
统一日志配置模块

提供企业级日志机制：
- 日志格式：时间 | 等级 | 模块 | 消息
- 日志等级：DEBUG / INFO / WARNING / ERROR / CRITICAL
- 双通道输出：控制台 + 文件
- 自动日志轮转：按大小 + 按时间
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

from app.core.config import settings

# 日志目录
LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志文件
LOG_FILE = LOG_DIR / "backend.log"
LOG_ERROR_FILE = LOG_DIR / "backend_error.log"

# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: Optional[str] = None) -> None:
    """初始化日志配置

    Args:
        level: 日志等级，默认读取 settings.LOG_LEVEL 或 DEBUG
    """
    log_level = level or getattr(settings, "LOG_LEVEL", None) or (
        "DEBUG" if settings.DEBUG else "INFO"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 清除已有的 handler（避免重复）
    root_logger.handlers.clear()

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件输出（全量日志，按大小轮转）
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(LOG_FILE),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 错误日志文件（仅 ERROR 及以上）
    error_handler = logging.handlers.RotatingFileHandler(
        filename=str(LOG_ERROR_FILE),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)


def get_logger(name: str) -> logging.Logger:
    """获取模块级 logger

    Args:
        name: 模块名称，使用 __name__ 调用

    Returns:
        配置好的 logger 实例
    """
    return logging.getLogger(name)
