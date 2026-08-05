"""
模型配置与 Token 管理
"""
from pydantic import BaseModel


class ModelConfig(BaseModel):
    name: str
    provider: str
    max_tokens: int
    temperature: float
    api_key: str = ""
    api_base: str = ""