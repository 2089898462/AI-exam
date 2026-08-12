"""
AI 健康检查 API 端点
验证 AI 服务配置和模型连接状态
"""
from fastapi import APIRouter

from app.core.config import AIConfig, validate_ai_config
from app.llm.provider import ModelProvider

router = APIRouter()


@router.get("")
async def ai_health_check():
    """AI 服务健康检查

    验证：
    1. 配置加载成功
    2. API Key 已配置（不显示 Key 内容）
    3. 模型名称和 Provider 正确
    """
    config = AIConfig()
    warnings = validate_ai_config()

    return {
        "status": "ok" if not warnings else "degraded",
        "service": "ai-scoring",
        "config": {
            "provider": config.MODEL_PROVIDER,
            "model": config.MODEL_NAME,
            "api_base": config.API_BASE,
            "api_key_configured": bool(config.API_KEY),
            "max_tokens": config.MAX_TOKENS,
            "temperature": config.TEMPERATURE,
        },
        "warnings": warnings if warnings else None,
    }


@router.post("/connectivity")
async def ai_connectivity_test():
    """AI 模型连接测试

    验证：
    1. 配置加载成功
    2. API Key 有效
    3. 模型可正常响应

    返回：
    - provider: 模型提供商
    - model: 模型名称
    - status: 连接状态
    - latency_ms: 响应延迟
    """
    import asyncio
    import time

    config = AIConfig()
    warnings = validate_ai_config()

    if warnings:
        return {
            "status": "failed",
            "message": "配置检查失败",
            "warnings": warnings,
        }

    if not config.API_KEY:
        return {
            "status": "failed",
            "message": "API Key 未配置",
            "provider": config.MODEL_PROVIDER,
            "model": config.MODEL_NAME,
        }

    start_time = time.time()
    provider = ModelProvider(config=config)

    try:
        result = await provider.chat(
            messages=[
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Reply with exactly: OK"},
            ],
            temperature=0.0,
            max_tokens=10,
        )

        latency_ms = (time.time() - start_time) * 1000

        if result.success and result.response:
            return {
                "status": "connected",
                "provider": config.MODEL_PROVIDER,
                "model": config.MODEL_NAME,
                "latency_ms": round(latency_ms, 1),
                "response_preview": result.response.content[:100],
            }
        else:
            return {
                "status": "failed",
                "provider": config.MODEL_PROVIDER,
                "model": config.MODEL_NAME,
                "error": result.error,
                "error_type": result.error_type,
                "latency_ms": round(latency_ms, 1),
            }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "status": "failed",
            "provider": config.MODEL_PROVIDER,
            "model": config.MODEL_NAME,
            "error": str(e),
            "error_type": "connection_error",
            "latency_ms": round(latency_ms, 1),
        }
    finally:
        await provider.close()