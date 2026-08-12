"""
安全启动检查
在应用启动时验证关键安全配置是否已正确设置。
"""
from __future__ import annotations

from app.core.config import settings


def validate_security_config() -> list[str]:
    """验证安全相关配置，返回警告列表（生产环境为空时也不抛异常）"""
    warnings: list[str] = []

    if not settings.JWT_SECRET_KEY:
        warnings.append(
            "[SECURITY] JWT_SECRET_KEY 未配置！"
            "必须通过 .env 文件或环境变量设置强随机密钥。"
        )
    elif settings.JWT_SECRET_KEY in (
        "change-me-in-production-please",
        "secret",
        "changeme",
    ):
        warnings.append(
            "[SECURITY] JWT_SECRET_KEY 使用了弱默认值，生产环境必须替换为强随机密钥！"
        )

    if not settings.DATABASE_URL:
        warnings.append(
            "[SECURITY] DATABASE_URL 未配置！"
            "必须通过 .env 文件或环境变量设置数据库连接字符串。"
        )

    return warnings


def check_production_safety() -> list[str]:
    """检查生产环境安全性"""
    warnings: list[str] = []

    if settings.DEBUG:
        warnings.append(
            "[SECURITY] DEBUG=True 在生产环境中不安全！"
            "请设置环境变量 DEBUG=False。"
        )

    return warnings
