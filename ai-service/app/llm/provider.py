"""
Model Provider 模块

提供大模型调用的统一封装：
- 模型切换支持
- 调用参数标准化
- 异常统一处理
- 调用审计（不记录敏感数据）

AI Agent 通过此模块调用大模型，不直接使用 LLMClient。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.config import AIConfig
from app.core.logger import log_ai_error, log_ai_request, log_ai_response
from app.llm.client import LLMClient
from app.llm.models import ModelConfig


class LLMProvider(str, Enum):
    """支持的 LLM 提供商"""
    DASHSCOPE = "dashscope"
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMResponse:
    """统一的 LLM 响应结构"""
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return bool(self.content)


@dataclass
class LLMCallResult:
    """LLM 调用结果（包含状态信息）"""
    success: bool
    response: LLMResponse | None = None
    error: str | None = None
    error_type: str | None = None  # timeout / model_error / rate_limit / unknown
    trace_id: str | None = None


class ModelProvider:
    """统一模型调用 Provider

    封装 LLMClient，提供：
    - 标准化调用接口
    - 统一异常处理
    - 调用审计信息
    """

    def __init__(self, config: AIConfig | None = None):
        self._config = config or AIConfig()
        self._client: LLMClient | None = None

    def _get_client(self) -> LLMClient:
        """获取或创建 LLM 客户端"""
        if self._client is None:
            model_config = ModelConfig(
                name=self._config.MODEL_NAME,
                provider=self._config.MODEL_PROVIDER,
                max_tokens=self._config.MAX_TOKENS,
                temperature=self._config.TEMPERATURE,
                api_key=self._config.API_KEY,
                api_base=self._config.API_BASE,
            )
            self._client = LLMClient(model_config)
        return self._client

    async def chat(
        self,
        messages: list[dict[str, str]],
        trace_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMCallResult:
        """发送对话请求

        Args:
            messages: 消息列表
            trace_id: 链路追踪 ID
            temperature: 温度参数
            max_tokens: 最大 Token 数

        Returns:
            LLMCallResult: 统一调用结果
        """
        start_time = time.time()
        endpoint = f"chat/{self._config.MODEL_PROVIDER}"

        log_ai_request(
            endpoint=endpoint,
            model=self._config.MODEL_NAME,
            prompt_version="chat",
            input_size=len(str(messages)),
        )

        try:
            client = self._get_client()
            raw_content = await client.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            latency_ms = (time.time() - start_time) * 1000

            log_ai_response(
                endpoint=endpoint,
                status="success",
                latency_ms=latency_ms,
                output_size=len(raw_content),
            )

            response = LLMResponse(
                content=raw_content,
                model=self._config.MODEL_NAME,
                latency_ms=latency_ms,
            )

            return LLMCallResult(
                success=True,
                response=response,
                trace_id=trace_id,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = self._classify_error(e)

            log_ai_error(
                endpoint=endpoint,
                error_type=error_type,
                error_msg=str(e),
                latency_ms=latency_ms,
            )

            return LLMCallResult(
                success=False,
                response=None,
                error=str(e),
                error_type=error_type,
                trace_id=trace_id,
            )

    def _classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        error_msg = str(error).lower()

        if "timeout" in error_msg or "timed out" in error_msg:
            return "timeout"
        if "rate limit" in error_msg or "429" in error_msg or "too many requests" in error_msg:
            return "rate_limit"
        if hasattr(error, "status_code") and error.status_code == 401:
            return "auth_error"
        if hasattr(error, "status_code") and error.status_code == 404:
            return "model_not_found"
        if "unauthorized" in error_msg or "authentication" in error_msg:
            return "auth_error"
        if "not found" in error_msg and "model" in error_msg:
            return "model_not_found"
        return "model_error"

    async def close(self) -> None:
        """关闭客户端连接"""
        if self._client:
            await self._client.close()
            self._client = None


# 全局默认 Provider 实例
_default_provider: ModelProvider | None = None


def get_provider() -> ModelProvider:
    """获取默认 Model Provider"""
    global _default_provider
    if _default_provider is None:
        _default_provider = ModelProvider()
    return _default_provider
