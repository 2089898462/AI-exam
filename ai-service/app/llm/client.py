"""
大模型调用客户端
封装 OpenAI 兼容接口调用（支持任意兼容 OpenAI API 的模型服务）
"""
from typing import Any

import httpx

from app.llm.models import ModelConfig


class LLMClient:
    """统一大模型调用客户端"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self._client = httpx.AsyncClient(timeout=60.0)

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """发送对话请求"""
        payload = {
            "model": self.config.name,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.config.api_base}/chat/completions"

        resp = await self._client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def close(self) -> None:
        await self._client.aclose()


def create_client(config: ModelConfig) -> LLMClient:
    """创建 LLM 客户端实例"""
    return LLMClient(config)
