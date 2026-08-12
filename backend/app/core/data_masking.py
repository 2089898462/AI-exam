"""
数据脱敏中间件

在数据返回前对敏感字段进行脱敏处理。
支持扩展规则，不写死业务字段。

脱敏规则：
- 手机号：13812345678 → 138****5678
- 邮箱：test@example.com → t***@example.com
- 身份证：110101199001011234 → 110101**********1234

注意：
- 本中间件基于字段名匹配，不检查字段内容
- 仅处理 JSON 响应
- 脱敏在返回给客户端前执行
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

from fastapi import FastAPI, Request, Response


# ============================================================
# 脱敏规则
# ============================================================

class MaskingRule:
    """脱敏规则基类"""

    def match(self, key: str) -> bool:
        """判断字段名是否匹配此规则"""
        raise NotImplementedError

    def mask(self, value: str) -> str:
        """脱敏处理"""
        raise NotImplementedError


class PhoneMaskingRule(MaskingRule):
    """手机号脱敏：13812345678 → 138****5678"""

    KEY_PATTERNS = ["phone", "mobile", "phone_number", "candidate_phone"]

    def match(self, key: str) -> bool:
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in self.KEY_PATTERNS)

    def mask(self, value: str) -> str:
        if not value or not isinstance(value, str):
            return value
        # 纯手机号格式
        if re.match(r'^1[3-9]\d{9}$', value):
            return value[:3] + "****" + value[7:]
        # 带区号或其他格式
        if len(value) >= 7:
            return value[:3] + "****" + value[-4:]
        return value


class EmailMaskingRule(MaskingRule):
    """邮箱脱敏：test@example.com → t***@example.com"""

    KEY_PATTERNS = ["email", "mail", "candidate_email"]

    def match(self, key: str) -> bool:
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in self.KEY_PATTERNS)

    def mask(self, value: str) -> str:
        if not value or not isinstance(value, str):
            return value
        if "@" not in value:
            return value
        local_part, domain = value.split("@", 1)
        if len(local_part) <= 2:
            return local_part[0] + "*@" + domain
        # 规则：首字符 + *** + @domain
        return local_part[0] + "***@" + domain


class IdCardMaskingRule(MaskingRule):
    """身份证号脱敏：110101199001011234 → 110101**********1234"""

    KEY_PATTERNS = ["id_card", "idnumber", "id_number", "idcard", "identity_card"]

    def match(self, key: str) -> bool:
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in self.KEY_PATTERNS)

    def mask(self, value: str) -> str:
        if not value or not isinstance(value, str):
            return value
        if len(value) <= 8:
            return value
        return value[:6] + "********" + value[-4:]


class NameMaskingRule(MaskingRule):
    """姓名脱敏：张三 → 张*，欧阳娜娜 → 欧**娜

    注意：姓名脱敏可能影响业务使用，默认不启用。
    需通过配置显式开启。
    """

    KEY_PATTERNS = ["name", "candidate_name", "real_name", "display_name"]

    def __init__(self, enabled: bool = False):
        self._enabled = enabled

    def match(self, key: str) -> bool:
        if not self._enabled:
            return False
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in self.KEY_PATTERNS)

    def mask(self, value: str) -> str:
        if not value or not isinstance(value, str):
            return value
        if len(value) <= 1:
            return value
        if len(value) == 2:
            return value[0] + "*"
        return value[0] + "*" * (len(value) - 2) + value[-1]


# ============================================================
# 默认脱敏规则集合
# ============================================================

DEFAULT_RULES: list[MaskingRule] = [
    PhoneMaskingRule(),
    EmailMaskingRule(),
    IdCardMaskingRule(),
    NameMaskingRule(enabled=False),  # 默认关闭，按需开启
]


# ============================================================
# 脱敏处理函数
# ============================================================

def mask_value(key: str, value: Any, rules: list[MaskingRule] | None = None) -> Any:
    """根据规则脱敏单个字段值

    Args:
        key: 字段名
        value: 字段值
        rules: 脱敏规则列表（默认使用 DEFAULT_RULES）

    Returns:
        Any: 脱敏后的值
    """
    if rules is None:
        rules = DEFAULT_RULES

    if value is None:
        return None

    # 字符串脱敏
    if isinstance(value, str):
        for rule in rules:
            if rule.match(key):
                return rule.mask(value)
        return value

    # 列表脱敏
    if isinstance(value, list):
        return [mask_value(key, item, rules) for item in value]

    # 字典脱敏（递归）
    if isinstance(value, dict):
        return {k: mask_value(k, v, rules) for k, v in value.items()}

    return value


def mask_sensitive_data(obj: Any, rules: list[MaskingRule] | None = None) -> Any:
    """对整个数据结构进行脱敏

    Args:
        obj: 任意 JSON 可序列化对象
        rules: 脱敏规则列表

    Returns:
        Any: 脱敏后的数据
    """
    if rules is None:
        rules = DEFAULT_RULES

    if isinstance(obj, dict):
        return {
            key: mask_value(key, value, rules)
            for key, value in obj.items()
        }

    if isinstance(obj, list):
        return [mask_sensitive_data(item, rules) for item in obj]

    return obj


# ============================================================
# FastAPI 中间件注册
# ============================================================

def register_data_masking(
    app: FastAPI,
    enabled: bool = True,
    exclude_paths: list[str] | None = None,
) -> None:
    """注册数据脱敏中间件

    Args:
        app: FastAPI 应用实例
        enabled: 是否启用
        exclude_paths: 排除的路径前缀列表
    """
    if not enabled:
        return

    exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json", "/health"]

    @app.middleware("http")
    async def data_masking_middleware(
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        response = await call_next(request)

        # 排除路径
        if any(request.url.path.startswith(p) for p in exclude_paths):
            return response

        # 仅处理 JSON 响应
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                if body:
                    data = json.loads(body)
                    masked_data = mask_sensitive_data(data)
                    new_body = json.dumps(masked_data, ensure_ascii=False).encode("utf-8")
                    headers = dict(response.headers)
                    headers["content-length"] = str(len(new_body))
                    return Response(
                        content=new_body,
                        status_code=response.status_code,
                        media_type="application/json",
                        headers=headers,
                    )
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        return response


# ============================================================
# 便捷函数：手动脱敏（用于 Service 层）
# ============================================================

def mask_phone(phone: str) -> str:
    """便捷手机号脱敏"""
    rule = PhoneMaskingRule()
    return rule.mask(phone) if rule.match("phone") else phone


def mask_email(email: str) -> str:
    """便捷邮箱脱敏"""
    rule = EmailMaskingRule()
    return rule.mask(email) if rule.match("email") else email