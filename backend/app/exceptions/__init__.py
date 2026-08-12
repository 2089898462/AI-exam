"""
统一异常定义

使用方式：
    raise NotFoundException("考试不存在")
    raise BusinessException("考试已发布，无法修改")
    raise ValidationException("参数错误")
"""
from typing import Any


class AppException(Exception):
    """应用基础异常"""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data


class NotFoundException(AppException):
    """资源不存在 (404)"""

    def __init__(self, message: str = "资源不存在", data: Any = None):
        super().__init__(code=404, message=message, data=data)


class BusinessException(AppException):
    """业务逻辑异常 (400)"""

    def __init__(self, message: str = "业务异常", data: Any = None, error_code: str = ""):
        self.error_code = error_code
        super().__init__(code=400, message=message, data=data)


class ValidationException(AppException):
    """参数校验异常 (422)"""

    def __init__(self, message: str = "参数校验失败", data: Any = None):
        super().__init__(code=422, message=message, data=data)


class UnauthorizedException(AppException):
    """未授权 (401)"""

    def __init__(self, message: str = "未授权访问"):
        super().__init__(code=401, message=message)


class ForbiddenException(AppException):
    """无权限 (403)"""

    def __init__(self, message: str = "无操作权限"):
        super().__init__(code=403, message=message)