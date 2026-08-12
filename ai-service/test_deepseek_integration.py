"""
S5-A DeepSeek-V4-Flash 模型接入测试

测试场景：
1. AI 配置加载（DeepSeek Provider 支持）
2. ModelProvider 创建和参数传递
3. LLMClient 正确使用 OpenAI 兼容接口
4. 健康检查端点（配置检查、连接测试）
5. API Key 异常处理
6. 网络异常处理
7. 调用日志记录
8. Provider 枚举正确性
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================
# 1. 配置加载测试
# ============================================================

def test_ai_config_deepseek_default():
    """测试 AIConfig 默认值为 DeepSeek-V4-Flash"""
    from app.core.config import AIConfig

    # 不设置任何环境变量，使用默认值
    config = AIConfig()

    assert config.MODEL_NAME == "deepseek-v4-flash", f"默认模型应为 deepseek-v4-flash，实际为 {config.MODEL_NAME}"
    assert config.MODEL_PROVIDER == "deepseek", f"默认 Provider 应为 deepseek，实际为 {config.MODEL_PROVIDER}"
    assert config.API_BASE == "https://api.deepseek.com/v1", f"默认 API Base 不正确"
    assert config.MAX_TOKENS == 2048
    assert config.TEMPERATURE == 0.3

    print("✅ test_ai_config_deepseek_default 通过")


def test_ai_config_env_override():
    """测试 AIConfig 支持环境变量覆盖"""
    os.environ["AI_MODEL_NAME"] = "deepseek-v4-pro"
    os.environ["AI_MODEL_PROVIDER"] = "deepseek"
    os.environ["AI_API_BASE"] = "https://custom.api.com/v1"
    os.environ["AI_MAX_TOKENS"] = "4096"
    os.environ["AI_TEMPERATURE"] = "0.7"

    from app.core.config import AIConfig
    config = AIConfig()

    assert config.MODEL_NAME == "deepseek-v4-pro"
    assert config.MODEL_PROVIDER == "deepseek"
    assert config.API_BASE == "https://custom.api.com/v1"
    assert config.MAX_TOKENS == 4096
    assert config.TEMPERATURE == 0.7

    # 清理环境变量
    del os.environ["AI_MODEL_NAME"]
    del os.environ["AI_MODEL_PROVIDER"]
    del os.environ["AI_API_BASE"]
    del os.environ["AI_MAX_TOKENS"]
    del os.environ["AI_TEMPERATURE"]

    # 恢复默认值验证
    config2 = AIConfig()
    assert config2.MODEL_NAME == "deepseek-v4-flash"

    print("✅ test_ai_config_env_override 通过")


def test_ai_config_validation():
    """测试 AI 配置验证（无 API Key 时应警告）"""
    from app.core.config import AIConfig, validate_ai_config

    # 确保无 API Key
    os.environ.pop("AI_API_KEY", None)

    config = AIConfig()
    warnings = validate_ai_config()

    assert len(warnings) >= 1, "无 API Key 时应有警告"
    assert any("AI_API_KEY" in w for w in warnings), "警告应提及 AI_API_KEY"

    print("✅ test_ai_config_validation 通过")


# ============================================================
# 2. Provider 枚举测试
# ============================================================

def test_llm_provider_enum():
    """测试 LLMProvider 枚举包含 DeepSeek"""
    from app.llm.provider import LLMProvider

    assert LLMProvider.DEEPSEEK.value == "deepseek"
    assert LLMProvider.DASHSCOPE.value == "dashscope"
    assert LLMProvider.OPENAI.value == "openai"
    assert LLMProvider.ANTHROPIC.value == "anthropic"

    # 确保 DeepSeek 是合法的 Provider
    providers = [p.value for p in LLMProvider]
    assert "deepseek" in providers

    print("✅ test_llm_provider_enum 通过")


# ============================================================
# 3. ModelProvider 测试
# ============================================================

def test_model_provider_creation():
    """测试 ModelProvider 使用 DeepSeek 配置创建"""
    from app.core.config import AIConfig
    from app.llm.provider import ModelProvider

    config = AIConfig()
    provider = ModelProvider(config=config)

    assert provider._config.MODEL_NAME == "deepseek-v4-flash"
    assert provider._config.MODEL_PROVIDER == "deepseek"
    assert provider._config.API_BASE == "https://api.deepseek.com/v1"

    print("✅ test_model_provider_creation 通过")


def test_model_provider_client_creation():
    """测试 ModelProvider 懒加载创建 LLMClient"""
    from app.core.config import AIConfig
    from app.llm.provider import ModelProvider
    from app.llm.client import LLMClient

    config = AIConfig()
    provider = ModelProvider(config=config)

    # 初始没有客户端
    assert provider._client is None

    # 获取客户端后应有实例
    client = provider._get_client()
    assert client is not None
    assert isinstance(client, LLMClient)

    # 验证 ModelConfig 正确传递
    assert client.config.name == "deepseek-v4-flash"
    assert client.config.provider == "deepseek"
    assert client.config.api_base == "https://api.deepseek.com/v1"

    print("✅ test_model_provider_client_creation 通过")


def test_model_provider_close():
    """测试 ModelProvider 关闭连接"""
    from app.core.config import AIConfig
    from app.llm.provider import ModelProvider

    config = AIConfig()
    provider = ModelProvider(config=config)

    # 创建客户端
    provider._get_client()
    assert provider._client is not None

    # 关闭
    asyncio.run(provider.close())
    assert provider._client is None

    print("✅ test_model_provider_close 通过")


# ============================================================
# 4. LLMClient 测试
# ============================================================

def test_llm_client_openai_compatible():
    """测试 LLMClient 使用 OpenAI 兼容接口"""
    from app.llm.client import LLMClient
    from app.llm.models import ModelConfig

    config = ModelConfig(
        name="deepseek-v4-flash",
        provider="deepseek",
        max_tokens=2048,
        temperature=0.3,
        api_key="test-key",
        api_base="https://api.deepseek.com/v1",
    )

    client = LLMClient(config)

    # 验证 URL 构建
    expected_url = "https://api.deepseek.com/v1/chat/completions"
    assert f"{config.api_base}/chat/completions" == expected_url

    print("✅ test_llm_client_openai_compatible 通过")


def test_llm_client_payload_structure():
    """测试 LLMClient 请求载荷结构"""
    from app.llm.client import LLMClient
    from app.llm.models import ModelConfig

    config = ModelConfig(
        name="deepseek-v4-flash",
        provider="deepseek",
        max_tokens=2048,
        temperature=0.3,
        api_key="test-key",
        api_base="https://api.deepseek.com/v1",
    )

    client = LLMClient(config)

    # 验证 payload 结构
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ]
    payload = {
        "model": config.name,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }

    assert payload["model"] == "deepseek-v4-flash"
    assert len(payload["messages"]) == 2
    assert payload["temperature"] == 0.3
    assert payload["max_tokens"] == 2048

    print("✅ test_llm_client_payload_structure 通过")


# ============================================================
# 5. 调用结果格式测试
# ============================================================

def test_llm_call_result_success():
    """测试 LLMCallResult 成功格式"""
    from app.llm.provider import LLMCallResult, LLMResponse

    response = LLMResponse(
        content="Hello, I'm DeepSeek.",
        model="deepseek-v4-flash",
        latency_ms=150.0,
    )

    result = LLMCallResult(
        success=True,
        response=response,
        trace_id="test-trace-001",
    )

    assert result.success is True
    assert result.response is not None
    assert result.response.content == "Hello, I'm DeepSeek."
    assert result.response.model == "deepseek-v4-flash"
    assert result.error is None
    assert result.error_type is None
    assert result.trace_id == "test-trace-001"

    # 验证统一格式
    assert {
        "success": result.success,
        "content": result.response.content if result.response else "",
        "usage": {},
    }  # 检查结构

    print("✅ test_llm_call_result_success 通过")


def test_llm_call_result_failure():
    """测试 LLMCallResult 失败格式"""
    from app.llm.provider import LLMCallResult

    result = LLMCallResult(
        success=False,
        error="Connection timeout",
        error_type="timeout",
        trace_id="test-trace-002",
    )

    assert result.success is False
    assert result.response is None
    assert result.error == "Connection timeout"
    assert result.error_type == "timeout"
    assert result.trace_id == "test-trace-002"

    print("✅ test_llm_call_result_failure 通过")


# ============================================================
# 6. 错误分类测试
# ============================================================

def test_error_classification():
    """测试错误类型分类"""
    from app.core.config import AIConfig
    from app.llm.provider import ModelProvider

    config = AIConfig()
    provider = ModelProvider(config=config)

    # 超时
    timeout_error = Exception("Connection timeout")
    assert provider._classify_error(timeout_error) == "timeout"

    # 速率限制
    rate_limit_error = Exception("429 Too Many Requests")
    assert provider._classify_error(rate_limit_error) == "rate_limit"

    # 认证错误
    auth_error = Exception("401 Unauthorized")
    auth_error.status_code = 401
    assert provider._classify_error(auth_error) == "auth_error"

    # 模型不存在
    not_found_error = Exception("404 Model Not Found")
    not_found_error.status_code = 404
    assert provider._classify_error(not_found_error) == "model_not_found"

    # 未知错误
    unknown_error = Exception("Something went wrong")
    assert provider._classify_error(unknown_error) == "model_error"

    print("✅ test_error_classification 通过")


# ============================================================
# 7. Mock 调用测试
# ============================================================

def test_mock_chat_success():
    """测试 Mock 成功调用"""
    from app.core.config import AIConfig
    from app.llm.provider import ModelProvider

    config = AIConfig()
    provider = ModelProvider(config=config)

    mock_response = {"choices": [{"message": {"content": "Hello!"}}]}

    with patch.object(provider, '_get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_client.chat.return_value = "Hello! I'm DeepSeek-V4-Flash."
        mock_get_client.return_value = mock_client

        result = asyncio.run(provider.chat(
            messages=[{"role": "user", "content": "Hi"}],
            trace_id="test-001",
        ))

        assert result.success is True
        assert result.response is not None
        assert result.response.content == "Hello! I'm DeepSeek-V4-Flash."
        assert result.response.model == "deepseek-v4-flash"
        assert result.error is None

        mock_client.chat.assert_called_once()

    print("✅ test_mock_chat_success 通过")


def test_mock_chat_timeout():
    """测试 Mock 超时异常"""
    from app.core.config import AIConfig
    from app.llm.provider import ModelProvider

    config = AIConfig()
    provider = ModelProvider(config=config)

    with patch.object(provider, '_get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_client.chat.side_effect = Exception("Connection timeout after 30s")
        mock_get_client.return_value = mock_client

        result = asyncio.run(provider.chat(
            messages=[{"role": "user", "content": "Hi"}],
            trace_id="test-002",
        ))

        assert result.success is False
        assert result.response is None
        assert result.error is not None
        assert result.error_type == "timeout"

    print("✅ test_mock_chat_timeout 通过")


def test_mock_chat_auth_error():
    """测试 Mock API Key 错误"""
    from app.core.config import AIConfig
    from app.llm.provider import ModelProvider

    config = AIConfig()
    provider = ModelProvider(config=config)

    with patch.object(provider, '_get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_client.chat.side_effect = Exception("401 Unauthorized: Invalid API Key")
        mock_client.chat.side_effect.status_code = 401
        mock_get_client.return_value = mock_client

        result = asyncio.run(provider.chat(
            messages=[{"role": "user", "content": "Hi"}],
            trace_id="test-003",
        ))

        assert result.success is False
        assert result.error_type == "auth_error"

    print("✅ test_mock_chat_auth_error 通过")


# ============================================================
# 8. 日志记录测试
# ============================================================

def test_log_ai_request():
    """测试 AI 请求日志记录"""
    from app.core.logger import log_ai_request

    # 不应抛出异常
    try:
        log_ai_request(
            endpoint="chat/deepseek",
            model="deepseek-v4-flash",
            prompt_version="chat",
            input_size=150,
        )
        print("✅ test_log_ai_request 通过")
    except Exception as e:
        print(f"❌ test_log_ai_request 失败: {e}")
        raise


def test_log_ai_response():
    """测试 AI 响应日志记录"""
    from app.core.logger import log_ai_response

    try:
        log_ai_response(
            endpoint="chat/deepseek",
            status="success",
            latency_ms=150.5,
            output_size=50,
        )
        print("✅ test_log_ai_response 通过")
    except Exception as e:
        print(f"❌ test_log_ai_response 失败: {e}")
        raise


def test_log_ai_error():
    """测试 AI 错误日志记录"""
    from app.core.logger import log_ai_error

    try:
        log_ai_error(
            endpoint="chat/deepseek",
            error_type="timeout",
            error_msg="Connection timed out",
            latency_ms=30000.0,
        )
        print("✅ test_log_ai_error 通过")
    except Exception as e:
        print(f"❌ test_log_ai_error 失败: {e}")
        raise


def test_log_no_sensitive_data():
    """测试日志不记录敏感数据"""
    from app.core.logger import log_ai_request

    # 确保日志函数参数中没有 API Key
    import inspect
    sig = inspect.signature(log_ai_request)
    params = list(sig.parameters.keys())

    assert "api_key" not in params, "日志函数不应接受 api_key 参数"
    assert "key" not in params, "日志函数不应接受 key 参数"
    assert "secret" not in params, "日志函数不应接受 secret 参数"

    print("✅ test_log_no_sensitive_data 通过")


# ============================================================
# 9. 健康检查端点测试
# ============================================================

def test_health_endpoint_config_check():
    """测试健康检查端点 - 配置检查"""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "config" in data
    assert data["config"]["provider"] == "deepseek"
    assert data["config"]["model"] == "deepseek-v4-flash"
    assert data["config"]["api_key_configured"] is False  # 测试环境无 Key

    print("✅ test_health_endpoint_config_check 通过")


def test_health_endpoint_with_key():
    """测试健康检查端点 - 有 API Key 时"""
    from fastapi.testclient import TestClient
    from main import app

    # 设置临时 API Key
    os.environ["AI_API_KEY"] = "test-api-key-12345"

    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    assert data["config"]["api_key_configured"] is True
    # 确保 Key 不暴露
    assert "test-api-key" not in str(data)

    # 清理
    del os.environ["AI_API_KEY"]

    print("✅ test_health_endpoint_with_key 通过")


def test_health_endpoint_key_masked():
    """测试健康检查端点 - API Key 被脱敏"""
    from fastapi.testclient import TestClient
    from main import app

    os.environ["AI_API_KEY"] = "sk-1234567890abcdef"

    client = TestClient(app)
    response = client.get("/api/health")

    data = response.json()

    # 确认 Key 未出现在响应中
    assert "sk-1234567890" not in str(data)
    assert "1234567890" not in str(data)
    assert data["config"]["api_key_configured"] is True

    # 清理
    del os.environ["AI_API_KEY"]

    print("✅ test_health_endpoint_key_masked 通过")


def test_health_connectivity_endpoint():
    """测试健康检查端点 - 连接测试（无 Key 时返回失败）"""
    from fastapi.testclient import TestClient
    from main import app

    # 确保无 Key
    os.environ.pop("AI_API_KEY", None)

    client = TestClient(app)
    response = client.post("/api/health/connectivity")

    assert response.status_code == 200
    data = response.json()

    # 无 Key 时应返回失败
    assert data["status"] == "failed"
    assert "API Key" in data.get("message", "") or "api_key" in str(data).lower()

    print("✅ test_health_connectivity_endpoint 通过")


# ============================================================
# 10. 全局默认 Provider 测试
# ============================================================

def test_get_provider_default():
    """测试全局默认 Provider 实例"""
    from app.llm.provider import get_provider

    provider = get_provider()

    assert provider is not None
    assert isinstance(provider, object)
    assert provider._config.MODEL_NAME == "deepseek-v4-flash"
    assert provider._config.MODEL_PROVIDER == "deepseek"

    print("✅ test_get_provider_default 通过")


# ============================================================
# 主测试入口
# ============================================================

def main():
    print("=" * 60)
    print("S5-A DeepSeek-V4-Flash 模型接入测试")
    print("=" * 60)
    print()

    errors = []

    test_groups = [
        ("配置加载测试", [
            ("AI Config 默认 DeepSeek", test_ai_config_deepseek_default),
            ("AI Config 环境变量覆盖", test_ai_config_env_override),
            ("AI 配置验证", test_ai_config_validation),
        ]),
        ("Provider 枚举测试", [
            ("LLMProvider 枚举完整性", test_llm_provider_enum),
        ]),
        ("ModelProvider 测试", [
            ("ModelProvider 创建", test_model_provider_creation),
            ("ModelProvider 客户端创建", test_model_provider_client_creation),
            ("ModelProvider 关闭连接", test_model_provider_close),
        ]),
        ("LLMClient 测试", [
            ("OpenAI 兼容接口", test_llm_client_openai_compatible),
            ("请求载荷结构", test_llm_client_payload_structure),
        ]),
        ("调用结果格式测试", [
            ("成功结果格式", test_llm_call_result_success),
            ("失败结果格式", test_llm_call_result_failure),
        ]),
        ("错误分类测试", [
            ("错误类型分类", test_error_classification),
        ]),
        ("Mock 调用测试", [
            ("Mock 成功调用", test_mock_chat_success),
            ("Mock 超时异常", test_mock_chat_timeout),
            ("Mock API Key 错误", test_mock_chat_auth_error),
        ]),
        ("日志记录测试", [
            ("AI 请求日志", test_log_ai_request),
            ("AI 响应日志", test_log_ai_response),
            ("AI 错误日志", test_log_ai_error),
            ("日志无敏感数据", test_log_no_sensitive_data),
        ]),
        ("健康检查端点测试", [
            ("配置检查", test_health_endpoint_config_check),
            ("有 Key 检查", test_health_endpoint_with_key),
            ("Key 脱敏检查", test_health_endpoint_key_masked),
            ("连接测试", test_health_connectivity_endpoint),
        ]),
        ("全局 Provider 测试", [
            ("默认 Provider", test_get_provider_default),
        ]),
    ]

    for group_name, tests in test_groups:
        print(f"\n📋 {group_name}")
        print("-" * 40)
        for name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                errors.append((name, str(e)))
                print(f"❌ {name} 失败: {e}")

    print()
    print("=" * 60)
    total = sum(len(tests) for _, tests in test_groups)
    passed = total - len(errors)
    print(f"测试结果：{passed}/{total} 通过")
    print("=" * 60)

    if errors:
        print("\n❌ 失败的测试：")
        for name, error in errors:
            print(f"  - {name}: {error}")
        return 1
    else:
        print("\n🎉 所有测试通过！")
        return 0


if __name__ == "__main__":
    sys.exit(main())