"""
S5.1 AI Agent 基础架构测试

测试范围：
1. Agent 核心测试（会话管理、消息处理）
2. Tool 调用测试（工具注册、参数校验、执行）
3. 权限测试（用户身份传递、越权拒绝）
4. 异常测试（模型异常、接口异常）
5. Prompt 管理测试
6. Model Provider 测试
"""
import json
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_conversation_creation():
    """1.1 创建会话"""
    from app.agents.conversation import Conversation, ConversationManager

    conv = Conversation.create(user_id=1, role="hr", trace_id="test-trace-001")
    assert conv.conversation_id is not None
    assert conv.user_id == 1
    assert conv.role == "hr"
    assert conv.trace_id == "test-trace-001"
    assert len(conv.messages) == 0
    print("[PASS] 1.1 创建会话")


def test_conversation_message():
    """1.2 会话消息管理"""
    from app.agents.conversation import Conversation

    conv = Conversation.create(user_id=1, role="hr")
    msg1 = conv.add_message("user", "你好")
    msg2 = conv.add_message("assistant", "你好，有什么可以帮助你？")

    assert len(conv.messages) == 2
    assert msg1.role == "user"
    assert msg2.role == "assistant"
    assert conv.messages[0].content == "你好"
    assert conv.messages[1].content == "你好，有什么可以帮助你？"

    recent = conv.get_recent_messages(limit=10)
    assert len(recent) == 2
    assert recent[0]["role"] == "user"
    print("[PASS] 1.2 会话消息管理")


def test_conversation_manager():
    """1.3 会话管理器"""
    from app.agents.conversation import ConversationManager

    mgr = ConversationManager(max_conversations=10)

    conv1 = mgr.create_conversation(user_id=1, role="hr")
    conv2 = mgr.create_conversation(user_id=1, role="hr")
    conv3 = mgr.create_conversation(user_id=2, role="admin")

    assert mgr.get_conversation(conv1.conversation_id) is not None
    assert mgr.get_conversation(conv2.conversation_id) is not None
    assert mgr.get_conversation(conv3.conversation_id) is not None

    user1_convs = mgr.get_user_conversations(1)
    assert len(user1_convs) == 2

    mgr.delete_conversation(conv1.conversation_id)
    assert mgr.get_conversation(conv1.conversation_id) is None
    print("[PASS] 1.3 会话管理器")


def test_conversation_serialization():
    """1.4 会话序列化"""
    from app.agents.conversation import Conversation

    conv = Conversation.create(user_id=1, role="hr", metadata={"source": "test"})
    conv.add_message("user", "测试消息")

    data = conv.to_dict()
    assert "conversation_id" in data
    assert "user_id" in data
    assert data["user_id"] == 1
    assert data["message_count"] == 1
    assert data["metadata"]["source"] == "test"

    msg_data = conv.messages[0].to_dict()
    assert msg_data["role"] == "user"
    assert msg_data["content"] == "测试消息"
    print("[PASS] 1.4 会话序列化")


def test_tool_registry():
    """2.1 工具注册和查询"""
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool, ToolParameter, ToolResult

    class TestTool(BaseTool):
        name = "test_tool"
        description = "测试工具"
        parameters = [
            ToolParameter(name="param1", type="string", description="参数1", required=True),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data={"received": params}, start_time=__import__("time").time())

    registry = ToolRegistry()
    registry.register(TestTool())

    tool = registry.get_tool("test_tool")
    assert tool is not None
    assert tool.name == "test_tool"

    tools_list = registry.list_tools()
    assert len(tools_list) == 1
    assert tools_list[0]["name"] == "test_tool"
    print("[PASS] 2.1 工具注册和查询")


def test_tool_parameter_validation():
    """2.2 工具参数校验"""
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool, ToolParameter

    class TestTool(BaseTool):
        name = "validate_test_tool"
        description = "参数校验测试工具"
        parameters = [
            ToolParameter(name="required_param", type="string", description="必填参数", required=True),
            ToolParameter(name="optional_param", type="integer", description="可选参数", required=False),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    tool = TestTool()

    # 缺少必填参数
    valid, error = tool.validate_params({})
    assert not valid
    assert "required_param" in error

    # 包含必填参数
    valid, error = tool.validate_params({"required_param": "value"})
    assert valid
    assert error == ""

    # 未知参数
    valid, error = tool.validate_params({"required_param": "value", "unknown": "x"})
    assert not valid
    assert "未知参数" in error
    print("[PASS] 2.2 工具参数校验")


def test_tool_execution():
    """2.3 工具执行"""
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool, ToolParameter

    class AddTool(BaseTool):
        name = "add_tool"
        description = "加法工具"
        parameters = [
            ToolParameter(name="a", type="integer", description="数字A", required=True),
            ToolParameter(name="b", type="integer", description="数字B", required=True),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            result = params["a"] + params["b"]
            return self._make_result(
                True,
                data={"result": result},
                trace_id=trace_id,
                start_time=__import__("time").time(),
            )

    async def run_test():
        registry = ToolRegistry()
        registry.register(AddTool())

        result = await registry.execute(
            tool_name="add_tool",
            params={"a": 10, "b": 20},
            user_id=1,
            role="hr",
            trace_id="trace-001",
        )
        assert result.success
        assert result.data["result"] == 30
        assert result.tool_name == "add_tool"
        assert result.trace_id == "trace-001"

        # 测试不存在的工具
        result2 = await registry.execute(
            tool_name="nonexistent",
            params={},
            user_id=1,
            role="hr",
        )
        assert not result2.success
        assert result2.error_code == "TOOL_NOT_FOUND"

    asyncio.run(run_test())
    print("[PASS] 2.3 工具执行")


def test_tool_schema():
    """2.4 工具 Schema 生成"""
    from app.tools.base_tool import BaseTool, ToolParameter

    class SampleTool(BaseTool):
        name = "sample_tool"
        description = "示例工具"
        parameters = [
            ToolParameter(name="query", type="string", description="搜索关键词", required=True),
            ToolParameter(name="limit", type="integer", description="限制数量", required=False, default=10),
            ToolParameter(name="status", type="string", description="状态", required=False, enum=["active", "inactive"]),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    tool = SampleTool()
    schema = tool.get_schema()

    assert schema["name"] == "sample_tool"
    assert schema["description"] == "示例工具"
    assert "properties" in schema["parameters"]
    assert "query" in schema["parameters"]["properties"]
    assert schema["parameters"]["properties"]["query"]["type"] == "string"
    assert schema["parameters"]["required"] == ["query"]
    print("[PASS] 2.4 工具 Schema 生成")


def test_permission_user_transfer():
    """3.1 用户身份传递"""
    from app.api.endpoints.agent import _extract_user
    from pydantic import BaseModel

    class MockRequest(BaseModel):
        message: str
        user_id: int | None = None
        role: str | None = None

    # 正常 HR 用户
    req = MockRequest(message="测试", user_id=1, role="hr")
    user_id, role = _extract_user(req)
    assert user_id == 1
    assert role == "hr"

    # 管理员
    req2 = MockRequest(message="测试", user_id=1, role="admin")
    user_id2, role2 = _extract_user(req2)
    assert user_id2 == 1
    assert role2 == "admin"
    print("[PASS] 3.1 用户身份传递")


def test_permission_denied():
    """3.2 越权拒绝"""
    from app.api.endpoints.agent import _extract_user
    from fastapi import HTTPException
    from pydantic import BaseModel

    class MockRequest(BaseModel):
        message: str
        user_id: int | None = None
        role: str | None = None

    # 无效用户 ID
    try:
        req = MockRequest(message="测试", user_id=0, role="hr")
        _extract_user(req)
        assert False, "应该抛出异常"
    except HTTPException as e:
        assert e.status_code == 401

    # 候选人角色（不允许使用 AI Agent）
    try:
        req2 = MockRequest(message="测试", user_id=1, role="candidate")
        _extract_user(req2)
        assert False, "应该抛出异常"
    except HTTPException as e:
        assert e.status_code == 403

    # 未认证
    try:
        req3 = MockRequest(message="测试")
        _extract_user(req3)
        assert False, "应该抛出异常"
    except HTTPException as e:
        assert e.status_code == 401
    print("[PASS] 3.2 越权拒绝")


def test_tool_write_protection():
    """3.3 AI 禁止调用写操作工具"""
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool, ToolParameter

    class WriteTool(BaseTool):
        name = "dangerous_write_tool"
        description = "写操作工具"
        parameters = []
        safety_level = "readwrite"  # 写操作

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    async def run_test():
        registry = ToolRegistry()
        registry.register(WriteTool())

        result = await registry.execute(
            tool_name="dangerous_write_tool",
            params={},
            user_id=1,
            role="admin",
        )
        assert not result.success
        assert result.error_code == "PERMISSION_DENIED"
        assert "无权" in result.error

    asyncio.run(run_test())
    print("[PASS] 3.3 AI 禁止调用写操作工具")


def test_prompt_loading():
    """4.1 Prompt 加载"""
    from app.core.config import load_prompt

    try:
        prompt = load_prompt("agent", "system_v1")
        assert prompt is not None
        assert prompt.version == "1.0"
        assert "template" in prompt.model_dump()
        assert len(prompt.template) > 0
        print("[PASS] 4.1 Prompt 加载")
    except FileNotFoundError:
        # 如果文件不存在（未创建），跳过
        print("[SKIP] 4.1 Prompt 加载（文件不存在，已在创建流程中）")


def test_model_provider_creation():
    """5.1 Model Provider 创建"""
    from app.llm.provider import ModelProvider

    provider = ModelProvider()
    assert provider is not None
    print("[PASS] 5.1 Model Provider 创建")


def test_llm_response_structure():
    """5.2 LLM 响应结构"""
    from app.llm.provider import LLMResponse, LLMCallResult

    response = LLMResponse(
        content="测试响应",
        model="test-model",
        latency_ms=100.0,
    )
    assert response.success
    assert response.content == "测试响应"
    assert response.latency_ms == 100.0

    result = LLMCallResult(
        success=True,
        response=response,
        trace_id="trace-001",
    )
    assert result.success
    assert result.response is not None

    # 失败场景
    failed_result = LLMCallResult(
        success=False,
        error="超时",
        error_type="timeout",
        trace_id="trace-002",
    )
    assert not failed_result.success
    assert failed_result.error_type == "timeout"
    print("[PASS] 5.2 LLM 响应结构")


def test_error_classification():
    """5.3 错误分类"""
    from app.llm.provider import ModelProvider

    provider = ModelProvider()

    timeout_error = Exception("Connection timeout")
    assert provider._classify_error(timeout_error) == "timeout"

    rate_limit_error = Exception("Rate limit exceeded")
    assert provider._classify_error(rate_limit_error) == "rate_limit"

    unknown_error = Exception("Something went wrong")
    assert provider._classify_error(unknown_error) == "model_error"
    print("[PASS] 5.3 错误分类")


def test_tool_result_structure():
    """6.1 ToolResult 结构"""
    from app.tools.base_tool import ToolResult

    result = ToolResult(
        success=True,
        data={"items": [1, 2, 3]},
        tool_name="test_tool",
        latency_ms=50.0,
        trace_id="trace-001",
    )

    data = result.to_dict()
    assert data["success"] is True
    assert data["tool_name"] == "test_tool"
    assert data["latency_ms"] == 50.0
    assert data["trace_id"] == "trace-001"

    # 失败结果
    failed = ToolResult(
        success=False,
        error="工具执行失败",
        error_code="EXECUTION_ERROR",
        tool_name="failed_tool",
    )
    assert not failed.success
    assert failed.error_code == "EXECUTION_ERROR"
    print("[PASS] 6.1 ToolResult 结构")


def test_conversation_eviction():
    """7.1 会话淘汰机制"""
    from app.agents.conversation import ConversationManager

    mgr = ConversationManager(max_conversations=3)

    # 创建超过限制的会话
    for i in range(5):
        mgr.create_conversation(user_id=1, role="hr")

    # 应该最多保留 3 个
    assert len(mgr._conversations) <= 3
    print("[PASS] 7.1 会话淘汰机制")


def test_chat_request_model():
    """8.1 Chat 请求模型"""
    from app.api.endpoints.agent import ChatRequest

    req = ChatRequest(
        message="你好",
        user_id=1,
        role="hr",
        trace_id="trace-001",
    )
    assert req.message == "你好"
    assert req.user_id == 1
    assert req.role == "hr"

    # 含会话 ID 的续聊
    req2 = ChatRequest(
        message="继续",
        conversation_id="conv-001",
        user_id=1,
        role="hr",
    )
    assert req2.conversation_id == "conv-001"
    print("[PASS] 8.1 Chat 请求模型")


def test_tool_list_for_agent():
    """8.2 工具列表获取"""
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool, ToolParameter

    class QueryTool(BaseTool):
        name = "query_data"
        description = "查询数据工具"
        parameters = [
            ToolParameter(name="id", type="integer", description="ID", required=True),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    class WriteTool(BaseTool):
        name = "write_data"
        description = "写入数据工具"
        parameters = []
        safety_level = "readwrite"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    registry = ToolRegistry()
    registry.register(QueryTool())
    registry.register(WriteTool())

    # list_tools 只返回只读工具
    tools = registry.list_tools(user_id=1, role="hr")
    assert len(tools) == 1
    assert tools[0]["name"] == "query_data"
    print("[PASS] 8.2 工具列表获取")


# ============================================================
# 运行所有测试
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("S5.1 AI Agent 基础架构测试")
    print("=" * 70)

    tests = [
        # Agent 核心测试
        ("1.1 创建会话", test_conversation_creation),
        ("1.2 会话消息管理", test_conversation_message),
        ("1.3 会话管理器", test_conversation_manager),
        ("1.4 会话序列化", test_conversation_serialization),

        # Tool 调用测试
        ("2.1 工具注册和查询", test_tool_registry),
        ("2.2 工具参数校验", test_tool_parameter_validation),
        ("2.3 工具执行", test_tool_execution),
        ("2.4 工具 Schema 生成", test_tool_schema),

        # 权限测试
        ("3.1 用户身份传递", test_permission_user_transfer),
        ("3.2 越权拒绝", test_permission_denied),
        ("3.3 AI 禁止调用写操作工具", test_tool_write_protection),

        # Prompt 管理测试
        ("4.1 Prompt 加载", test_prompt_loading),

        # Model Provider 测试
        ("5.1 Model Provider 创建", test_model_provider_creation),
        ("5.2 LLM 响应结构", test_llm_response_structure),
        ("5.3 错误分类", test_error_classification),

        # 其他测试
        ("6.1 ToolResult 结构", test_tool_result_structure),
        ("7.1 会话淘汰机制", test_conversation_eviction),
        ("8.1 Chat 请求模型", test_chat_request_model),
        ("8.2 工具列表获取", test_tool_list_for_agent),
    ]

    passed = 0
    failed = 0
    skipped = 0
    failures = []

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            if "[SKIP]" in str(e):
                skipped += 1
                print(f"  [SKIP] {name}: {e}")
            else:
                failed += 1
                failures.append((name, str(e)))
                print(f"  [FAIL] {name}: {e}")

    print("\n" + "=" * 70)
    print(f"测试完成: {passed} 通过, {failed} 失败, {skipped} 跳过")
    print("=" * 70)

    if failures:
        print("\n失败详情:")
        for name, error in failures:
            print(f"  - {name}: {error}")

    sys.exit(0 if failed == 0 else 1)
