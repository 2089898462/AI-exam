"""
认证依赖（兼容层）
实际实现已迁移到 app.core.dependencies
"""
from app.core.dependencies import (
    _extract_token,
    get_current_user,
    get_current_user_id_from_header,
    get_optional_current_user,
)
from app.core.permissions import require_roles

__all__ = [
    "_extract_token",
    "get_current_user",
    "get_current_user_id_from_header",
    "get_optional_current_user",
    "require_roles",
    "verify_roles",
]


def verify_roles(allowed_roles: list[str]):
    """角色校验依赖工厂（兼容旧名称）"""
    return require_roles(allowed_roles)
