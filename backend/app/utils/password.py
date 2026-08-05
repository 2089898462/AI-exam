"""
密码工具模块
兼容层：底层已迁移到 app.core.security
"""
from app.core.security import hash_password, verify_password

__all__ = ["hash_password", "verify_password"]
