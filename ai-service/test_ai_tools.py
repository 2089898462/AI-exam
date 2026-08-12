"""
S5.2 AI Tool 调用能力建设测试

测试范围：
1. Tool 注册测试（Tool 注册/查询/注销）
2. 参数校验测试（必填/类型/范围/枚举校验）
3. 权限测试（角色权限/越权拒绝/工具安全等级）
4. 审计测试（调用日志生成/查询/统计）
5. Tool Router 测试（统一调用流程/异常处理）
6. 返回格式测试（标准化格式/字段完整性）
7. 首批工具测试（统计查询/成绩查询/候选人历史）
"""
import json
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================
# 测试 1：Tool 注册
# ============================================================

def test_tool_registration():
    """1.1 Tool 注册和查询"""
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool, ToolParameter

    class QueryTool(BaseTool):
        name = "test_query_tool"
        description = "测试查询工具"
        parameters = [
            ToolParameter(name="id", type="integer", description="ID", required=True),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(
                True, data={"id": params["id"]}, message="查询成功",
                start_time=__import__("time").time(),
            )

    registry = ToolRegistry()
    registry.register(QueryTool())

    assert registry.get_tool("test_query_tool") is not None
    assert registry.get_tool("nonexistent") is None

    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "test_query_tool"
    print("[PASS] 1.1 Tool 注册和查询")


def test_tool_registration_duplicate():
    """1.2 重复注册拒绝"""
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool

    class DupTool(BaseTool):
        name = "dup_tool"
        description = "重复工具"
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    registry = ToolRegistry()
    registry.register(DupTool())

    try:
        registry.register(DupTool())
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "已注册" in str(e)
    print("[PASS] 1.2 重复注册拒绝")


def test_tool_unregister():
    """1.3 Tool 注销"""
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool

    class TempTool(BaseTool):
        name = "temp_tool"
        description = "临时工具"
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    registry = ToolRegistry()
    registry.register(TempTool())
    assert registry.get_tool("temp_tool") is not None

    registry.unregister("temp_tool")
    assert registry.get_tool("temp_tool") is None

    try:
        registry.unregister("nonexistent")
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass
    print("[PASS] 1.3 Tool 注销")


# ============================================================
# 测试 2：参数校验
# ============================================================

def test_param_required():
    """2.1 必填参数校验"""
    from app.tools.base_tool import BaseTool, ToolParameter

    class Tool(BaseTool):
        name = "param_test_tool"
        description = "参数测试工具"
        parameters = [
            ToolParameter(name="required_field", type="string", description="必填", required=True),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    tool = Tool()
    valid, error = tool.validate_params({})
    assert not valid
    assert "required_field" in error

    valid2, error2 = tool.validate_params({"required_field": "value"})
    assert valid2
    print("[PASS] 2.1 必填参数校验")


def test_param_type_validation():
    """2.2 参数类型校验"""
    from app.tools.base_tool import BaseTool, ToolParameter

    class Tool(BaseTool):
        name = "type_test_tool"
        description = "类型测试工具"
        parameters = [
            ToolParameter(name="count", type="integer", description="数量", required=True),
            ToolParameter(name="name", type="string", description="名称", required=True),
            ToolParameter(name="active", type="boolean", description="是否激活", required=False),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    tool = Tool()

    # 正确类型
    valid, _ = tool.validate_params({"count": 10, "name": "test", "active": True})
    assert valid

    # 错误类型
    valid, error = tool.validate_params({"count": "abc", "name": "test"})
    assert not valid
    assert "整数" in error

    valid, error = tool.validate_params({"count": 10, "name": 123})
    assert not valid
    assert "字符串" in error

    valid, error = tool.validate_params({"count": 10, "name": "test", "active": "yes"})
    assert not valid
    assert "布尔值" in error
    print("[PASS] 2.2 参数类型校验")


def test_param_range_validation():
    """2.3 参数范围校验"""
    from app.tools.base_tool import BaseTool, ToolParameter

    class Tool(BaseTool):
        name = "range_test_tool"
        description = "范围测试工具"
        parameters = [
            ToolParameter(name="score", type="integer", description="分数",
                         required=True, min_value=0, max_value=100),
            ToolParameter(name="status", type="string", description="状态",
                         required=False, enum=["active", "inactive"]),
            ToolParameter(name="keyword", type="string", description="关键词",
                         required=False, min_length=2, max_length=50),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    tool = Tool()

    # 范围校验
    valid, error = tool.validate_params({"score": -1})
    assert not valid
    assert "不能小于" in error

    valid, error = tool.validate_params({"score": 101})
    assert not valid
    assert "不能大于" in error

    valid, error = tool.validate_params({"score": 50})
    assert valid

    # 枚举校验
    valid, error = tool.validate_params({"score": 50, "status": "unknown"})
    assert not valid
    assert "必须为" in error

    valid, error = tool.validate_params({"score": 50, "status": "active"})
    assert valid

    # 长度校验
    valid, error = tool.validate_params({"score": 50, "keyword": "x"})
    assert not valid
    assert "长度" in error

    valid, error = tool.validate_params({"score": 50, "keyword": "ok"})
    assert valid
    print("[PASS] 2.3 参数范围校验")


def test_param_unknown_rejection():
    """2.4 未知参数拒绝"""
    from app.tools.base_tool import BaseTool, ToolParameter

    class Tool(BaseTool):
        name = "known_param_tool"
        description = "已知参数工具"
        parameters = [
            ToolParameter(name="valid_field", type="string", description="有效参数", required=False),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    tool = Tool()

    valid, error = tool.validate_params({"valid_field": "ok", "unknown_field": "bad"})
    assert not valid
    assert "未知参数" in error
    print("[PASS] 2.4 未知参数拒绝")


# ============================================================
# 测试 3：权限控制
# ============================================================

def test_role_permission_hr():
    """3.1 HR 角色权限"""
    from app.tools.tool_router import ToolRouter, AI_ALLOWED_ROLES
    assert "hr" in AI_ALLOWED_ROLES
    assert "admin" in AI_ALLOWED_ROLES
    assert "candidate" not in AI_ALLOWED_ROLES
    assert "employee" not in AI_ALLOWED_ROLES
    print("[PASS] 3.1 HR 角色权限")


def test_role_permission_denied():
    """3.2 无权限角色拒绝"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool

    class SafeTool(BaseTool):
        name = "safe_tool"
        description = "安全工具"
        parameters = []
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    async def run_test():
        registry = ToolRegistry()
        registry.register(SafeTool())
        router = ToolRouter(registry=registry)

        # 候选人角色 - 拒绝
        result = await router.call_tool(
            tool_name="safe_tool",
            params={},
            user_id=1,
            role="candidate",
            trace_id="trace-001",
        )
        assert not result.success
        assert result.error_code == "PERMISSION_DENIED"

        # 无效用户 ID - 拒绝
        result2 = await router.call_tool(
            tool_name="safe_tool",
            params={},
            user_id=0,
            role="hr",
            trace_id="trace-002",
        )
        assert not result2.success
        assert result2.error_code == "PERMISSION_DENIED"

    asyncio.run(run_test())
    print("[PASS] 3.2 无权限角色拒绝")


def test_write_tool_protection():
    """3.3 写操作工具保护"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool

    class WriteTool(BaseTool):
        name = "dangerous_write"
        description = "写操作工具"
        parameters = []
        safety_level = "readwrite"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    async def run_test():
        registry = ToolRegistry()
        registry.register(WriteTool())
        router = ToolRouter(registry=registry)

        # 即使 admin 也不能使用写操作工具
        result = await router.call_tool(
            tool_name="dangerous_write",
            params={},
            user_id=1,
            role="admin",
            trace_id="trace-001",
        )
        assert not result.success
        assert result.error_code == "PERMISSION_DENIED"

    asyncio.run(run_test())
    print("[PASS] 3.3 写操作工具保护")


# ============================================================
# 测试 4：Tool Router
# ============================================================

def test_tool_router_full_flow():
    """4.1 Tool Router 完整调用流程"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool, ToolParameter

    class QueryTool(BaseTool):
        name = "router_test_tool"
        description = "路由测试工具"
        parameters = [
            ToolParameter(name="keyword", type="string", description="关键词", required=True),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(
                True,
                data={"keyword": params["keyword"], "count": 42},
                message=f"查询成功，关键词 {params['keyword']} 匹配 42 条记录",
                trace_id=trace_id,
                start_time=__import__("time").time(),
            )

    async def run_test():
        registry = ToolRegistry()
        registry.register(QueryTool())
        router = ToolRouter(registry=registry)

        result = await router.call_tool(
            tool_name="router_test_tool",
            params={"keyword": "考试"},
            user_id=1,
            role="hr",
            trace_id="trace-flow-001",
        )

        print(f"\n[DEBUG 4.1] result.success={result.success}, error={result.error}, error_code={result.error_code}")
        print(f"[DEBUG 4.1] result.data={result.data}, result.message={result.message}")
        assert result.success, f"执行失败: {result.error}"
        assert result.tool_name == "router_test_tool", f"tool_name mismatch: {result.tool_name}"
        assert result.trace_id == "trace-flow-001", f"trace_id mismatch: {result.trace_id}"
        assert result.message, "message 不应为空"
        assert result.data is not None, "data 不应为 None"
        assert result.data["count"] == 42, f"count mismatch: {result.data.get('count') if result.data else 'N/A'}"

        # 审计日志已生成
        logs = router.get_audit_logs(tool_name="router_test_tool")
        print(f"[DEBUG 4.1] audit logs count: {len(logs)}")
        assert len(logs) >= 1, f"审计日志为空: {logs}"
        assert logs[0]["success"] is True, f"审计日志记录为失败: {logs[0]}"

    asyncio.run(run_test())
    print("[PASS] 4.1 Tool Router 完整调用流程")


def test_tool_router_exception_handling():
    """4.2 Tool Router 异常处理"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool

    class ErrorTool(BaseTool):
        name = "error_tool"
        description = "异常测试工具"
        parameters = []
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            raise RuntimeError("工具内部异常")

    async def run_test():
        registry = ToolRegistry()
        registry.register(ErrorTool())
        router = ToolRouter(registry=registry)

        result = await router.call_tool(
            tool_name="error_tool",
            params={},
            user_id=1,
            role="hr",
            trace_id="trace-err-001",
        )

        assert not result.success, "应该失败"
        assert result.error_code == "EXECUTION_ERROR"
        assert "工具内部异常" in result.error

        # 异常也必须记录审计日志
        logs = router.get_audit_logs(trace_id="trace-err-001")
        assert len(logs) >= 1, "审计日志未生成"
        assert logs[0]["success"] is False

    asyncio.run(run_test())
    print("[PASS] 4.2 Tool Router 异常处理")


def test_tool_router_not_found():
    """4.3 Tool Router 工具不存在"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry

    async def run_test():
        router = ToolRouter(registry=ToolRegistry())

        result = await router.call_tool(
            tool_name="nonexistent_tool",
            params={},
            user_id=1,
            role="hr",
            trace_id="trace-nf-001",
        )

        assert not result.success
        assert result.error_code == "TOOL_NOT_FOUND"

    asyncio.run(run_test())
    print("[PASS] 4.3 Tool Router 工具不存在")


# ============================================================
# 测试 5：审计日志
# ============================================================

def test_audit_log_generation():
    """5.1 审计日志生成"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool

    class AuditTool(BaseTool):
        name = "audit_test_tool"
        description = "审计测试工具"
        parameters = []
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data={"status": "ok"}, message="成功",
                                    start_time=__import__("time").time())

    async def run_test():
        registry = ToolRegistry()
        registry.register(AuditTool())
        router = ToolRouter(registry=registry)

        # 成功调用
        await router.call_tool("audit_test_tool", {}, user_id=1, role="hr", trace_id="audit-001")
        # 失败调用
        await router.call_tool("audit_test_tool", {"bad": "param"}, user_id=1, role="hr", trace_id="audit-002")

        logs = router.get_audit_logs()
        assert len(logs) == 2

        # 成功日志
        success_logs = router.get_audit_logs(success=True)
        assert len(success_logs) == 1
        assert success_logs[0]["tool_name"] == "audit_test_tool"

        # 失败日志
        fail_logs = router.get_audit_logs(success=False)
        assert len(fail_logs) == 1

    asyncio.run(run_test())
    print("[PASS] 5.1 审计日志生成")


def test_audit_log_query_by_trace_id():
    """5.2 按 trace_id 查询审计日志"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool

    class TraceTool(BaseTool):
        name = "trace_test_tool"
        description = "追踪测试工具"
        parameters = []
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    async def run_test():
        registry = ToolRegistry()
        registry.register(TraceTool())
        router = ToolRouter(registry=registry)

        await router.call_tool("trace_test_tool", {}, user_id=1, role="hr", trace_id="my-trace-123")

        log = router.get_audit_log_by_trace_id("my-trace-123")
        assert log is not None
        assert log["trace_id"] == "my-trace-123"
        assert log["tool_name"] == "trace_test_tool"
        assert log["user_id"] == 1
        assert log["success"] is True

        # 不存在的 trace_id
        assert router.get_audit_log_by_trace_id("nonexistent") is None

    asyncio.run(run_test())
    print("[PASS] 5.2 按 trace_id 查询审计日志")


def test_audit_log_user_filter():
    """5.3 按用户筛选审计日志"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool

    class UserTool(BaseTool):
        name = "user_test_tool"
        description = "用户测试工具"
        parameters = []
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    async def run_test():
        registry = ToolRegistry()
        registry.register(UserTool())
        router = ToolRouter(registry=registry)

        await router.call_tool("user_test_tool", {}, user_id=1, role="hr", trace_id="u1-001")
        await router.call_tool("user_test_tool", {}, user_id=2, role="admin", trace_id="u2-001")
        await router.call_tool("user_test_tool", {}, user_id=1, role="hr", trace_id="u1-002")

        user1_logs = router.get_audit_logs(user_id=1)
        assert len(user1_logs) == 2

        user2_logs = router.get_audit_logs(user_id=2)
        assert len(user2_logs) == 1

    asyncio.run(run_test())
    print("[PASS] 5.3 按用户筛选审计日志")


# ============================================================
# 测试 6：返回格式
# ============================================================

def test_standard_response_format():
    """6.1 标准化返回格式"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool, ToolParameter

    class FormatTool(BaseTool):
        name = "format_test_tool"
        description = "格式测试工具"
        parameters = [
            ToolParameter(name="query", type="string", description="查询", required=True),
        ]
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(
                True,
                data={"items": [1, 2, 3], "total": 3},
                message=f"查询成功: {params['query']}",
                start_time=__import__("time").time(),
            )

    async def run_test():
        registry = ToolRegistry()
        registry.register(FormatTool())
        router = ToolRouter(registry=registry)

        result = await router.call_tool(
            tool_name="format_test_tool",
            params={"query": "考试列表"},
            user_id=1,
            role="hr",
            trace_id="trace-format-001",
        )

        data = result.to_dict()

        # 必须包含的字段
        assert "success" in data
        assert "data" in data
        assert "message" in data
        assert "tool_name" in data
        assert "latency_ms" in data
        assert "trace_id" in data

        # 成功响应不应包含 error 字段
        assert "error" not in data
        assert "error_code" not in data

        assert data["success"] is True
        assert data["tool_name"] == "format_test_tool"
        assert data["message"] != ""

    asyncio.run(run_test())
    print("[PASS] 6.1 标准化返回格式")


def test_error_response_format():
    """6.2 错误返回格式"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry

    async def run_test():
        router = ToolRouter(registry=ToolRegistry())

        result = await router.call_tool(
            tool_name="missing_tool",
            params={},
            user_id=1,
            role="hr",
            trace_id="trace-err-fmt",
        )

        data = result.to_dict()

        # 错误响应必须包含 error 和 error_code
        assert data["success"] is False
        assert "error" in data
        assert "error_code" in data
        assert data["error_code"] == "TOOL_NOT_FOUND"

    asyncio.run(run_test())
    print("[PASS] 6.2 错误返回格式")


# ============================================================
# 测试 7：工具使用统计
# ============================================================

def test_tool_usage_stats():
    """7.1 工具使用统计"""
    from app.tools.tool_audit import ToolAuditService
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool

    class StatTool(BaseTool):
        name = "stat_test_tool"
        description = "统计测试工具"
        parameters = []
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    async def run_test():
        registry = ToolRegistry()
        registry.register(StatTool())
        router = ToolRouter(registry=registry)
        audit = ToolAuditService(router=router)

        # 调用 3 次
        for i in range(3):
            await router.call_tool("stat_test_tool", {}, user_id=1, role="hr",
                                   trace_id=f"stat-{i}")

        stats = audit.get_tool_usage_stats()
        assert stats["total_calls"] == 3
        assert "stat_test_tool" in stats["tool_stats"]
        tool_stat = stats["tool_stats"]["stat_test_tool"]
        assert tool_stat["total_calls"] == 3
        assert tool_stat["success_calls"] == 3
        assert "avg_latency_ms" in tool_stat

    asyncio.run(run_test())
    print("[PASS] 7.1 工具使用统计")


def test_recent_failures():
    """7.2 最近失败调用查询"""
    from app.tools.tool_audit import ToolAuditService
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry

    async def run_test():
        router = ToolRouter(registry=ToolRegistry())
        audit = ToolAuditService(router=router)

        # 触发失败调用
        await router.call_tool("missing", {}, user_id=1, role="hr", trace_id="fail-001")
        await router.call_tool("missing", {}, user_id=1, role="hr", trace_id="fail-002")

        failures = audit.get_recent_failures()
        assert len(failures) >= 2

    asyncio.run(run_test())
    print("[PASS] 7.2 最近失败调用查询")


# ============================================================
# 测试 8：可用工具列表
# ============================================================

def test_available_tools_list():
    """8.1 可用工具列表按角色过滤"""
    from app.tools.tool_router import ToolRouter
    from app.tools.tool_registry import ToolRegistry
    from app.tools.base_tool import BaseTool

    class AvailTool(BaseTool):
        name = "avail_test_tool"
        description = "可用工具测试"
        parameters = []
        safety_level = "readonly"

        async def execute(self, params, user_id, role, trace_id=None):
            return self._make_result(True, data="ok", start_time=__import__("time").time())

    async def run_test():
        registry = ToolRegistry()
        registry.register(AvailTool())
        router = ToolRouter(registry=registry)

        # HR 可以看到
        hr_tools = router.list_available_tools(user_id=1, role="hr")
        assert len(hr_tools) == 1
        assert hr_tools[0]["name"] == "avail_test_tool"

        # Admin 可以看到
        admin_tools = router.list_available_tools(user_id=1, role="admin")
        assert len(admin_tools) == 1

        # 候选人看不到
        candidate_tools = router.list_available_tools(user_id=1, role="candidate")
        assert len(candidate_tools) == 0

    asyncio.run(run_test())
    print("[PASS] 8.1 可用工具列表按角色过滤")


# ============================================================
# 测试 9：首批工具注册
# ============================================================

def test_first_batch_tools_exist():
    """9.1 首批 3 个工具已注册"""
    from app.tools.tool_registry import ToolRegistry
    from app.tools.exam_tools import register_exam_tools

    registry = ToolRegistry()
    register_exam_tools(registry)

    # S5.2 首批工具
    assert registry.get_tool("get_exam_statistics") is not None
    assert registry.get_tool("get_exam_results") is not None
    assert registry.get_tool("get_candidate_history") is not None

    # 验证 Schema 包含必要信息
    stats_tool = registry.get_tool("get_exam_statistics")
    schema = stats_tool.get_schema()
    assert schema["name"] == "get_exam_statistics"
    assert "描述" in schema["description"] or "统计" in schema["description"]

    results_tool = registry.get_tool("get_exam_results")
    assert results_tool is not None

    history_tool = registry.get_tool("get_candidate_history")
    assert history_tool is not None

    print("[PASS] 9.1 首批 3 个工具已注册")


# ============================================================
# 运行所有测试
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("S5.2 AI Tool 调用能力建设测试")
    print("=" * 70)

    tests = [
        # 1. Tool 注册
        ("1.1 Tool 注册和查询", test_tool_registration),
        ("1.2 重复注册拒绝", test_tool_registration_duplicate),
        ("1.3 Tool 注销", test_tool_unregister),

        # 2. 参数校验
        ("2.1 必填参数校验", test_param_required),
        ("2.2 参数类型校验", test_param_type_validation),
        ("2.3 参数范围校验", test_param_range_validation),
        ("2.4 未知参数拒绝", test_param_unknown_rejection),

        # 3. 权限控制
        ("3.1 HR 角色权限", test_role_permission_hr),
        ("3.2 无权限角色拒绝", test_role_permission_denied),
        ("3.3 写操作工具保护", test_write_tool_protection),

        # 4. Tool Router
        ("4.1 Tool Router 完整调用流程", test_tool_router_full_flow),
        ("4.2 Tool Router 异常处理", test_tool_router_exception_handling),
        ("4.3 Tool Router 工具不存在", test_tool_router_not_found),

        # 5. 审计日志
        ("5.1 审计日志生成", test_audit_log_generation),
        ("5.2 按 trace_id 查询审计日志", test_audit_log_query_by_trace_id),
        ("5.3 按用户筛选审计日志", test_audit_log_user_filter),

        # 6. 返回格式
        ("6.1 标准化返回格式", test_standard_response_format),
        ("6.2 错误返回格式", test_error_response_format),

        # 7. 统计
        ("7.1 工具使用统计", test_tool_usage_stats),
        ("7.2 最近失败调用查询", test_recent_failures),

        # 8. 可用工具
        ("8.1 可用工具列表按角色过滤", test_available_tools_list),

        # 9. 首批工具
        ("9.1 首批 3 个工具已注册", test_first_batch_tools_exist),
    ]

    passed = 0
    failed = 0
    failures = []

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            failures.append((name, str(e)))
            print(f"  [FAIL] {name}: {e}")

    print("\n" + "=" * 70)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 70)

    if failures:
        print("\n失败详情:")
        for name, error in failures:
            print(f"  - {name}: {error}")

    sys.exit(0 if failed == 0 else 1)
