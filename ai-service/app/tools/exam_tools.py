"""
考试相关 Tool 实现（S5.2 增强版）

封装 AI Agent 可调用的考试查询工具。
所有工具均为只读操作，通过 Backend API 获取数据。

S5.2 增强：
- 新增考试统计查询工具（get_exam_statistics）
- 所有工具返回标准化 message 字段
- 增强参数范围校验
- 统一审计集成

Backend API 调用通过 httpx 实现，统一处理：
- 用户身份透传（X-User-Id / X-User-Role Header）
- 异常处理
- 超时处理
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from app.core.config import AIConfig
from app.tools.base_tool import BaseTool, ToolParameter, ToolResult


# ============================================================
# Backend API 客户端
# ============================================================

class BackendClient:
    """Backend API 客户端

    AI Agent 通过此类调用 Backend API，不直接访问数据库。
    """

    def __init__(self, config: AIConfig | None = None):
        self._config = config or AIConfig()
        self._base_url = os.environ.get(
            "BACKEND_API_URL", "http://localhost:8000/api/v1"
        )
        self._timeout = float(os.environ.get("TOOL_TIMEOUT", "10.0"))

    async def get(
        self,
        path: str,
        user_id: int,
        role: str,
        params: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> tuple[bool, Any, str | None]:
        """发送 GET 请求

        Returns:
            tuple[bool, Any, str | None]: (是否成功, 响应数据, 错误信息)
        """
        try:
            headers = {
                "X-User-Id": str(user_id),
                "X-User-Role": role,
            }
            if trace_id:
                headers["X-Trace-Id"] = trace_id

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self._base_url}{path}",
                    params=params,
                    headers=headers,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 200:
                        return True, data.get("data"), None
                    else:
                        return False, None, data.get("message", "业务错误")
                elif resp.status_code == 403:
                    return False, None, "权限不足"
                elif resp.status_code == 404:
                    return False, None, "资源不存在"
                else:
                    return False, None, f"Backend 返回错误: HTTP {resp.status_code}"

        except httpx.TimeoutException:
            return False, None, "请求超时"
        except httpx.ConnectError:
            return False, None, "无法连接 Backend 服务"
        except Exception as e:
            return False, None, f"请求异常: {str(e)}"


# ============================================================
# 考试统计查询工具（S5.2 新增）
# ============================================================

class GetExamStatisticsTool(BaseTool):
    """获取考试统计数据（S5.2 首批工具）

    返回：
    - 参与人数
    - 完成人数
    - 平均成绩
    - 通过率
    """

    name = "get_exam_statistics"
    description = "获取指定考试的统计数据，包括参与人数、完成人数、平均成绩、通过率等核心指标。"
    safety_level = "readonly"

    parameters = [
        ToolParameter(
            name="exam_id",
            type="integer",
            description="考试 ID",
            required=True,
            min_value=1,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._client = BackendClient()

    async def execute(
        self,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        start_time = __import__("time").time()
        exam_id = params["exam_id"]

        success, data, error = await self._client.get(
            f"/exams/{exam_id}/statistics",
            user_id=user_id,
            role=role,
            trace_id=trace_id,
        )

        if success:
            return self._make_result(
                success=True,
                data=data,
                message=f"考试 {exam_id} 统计查询成功",
                trace_id=trace_id,
                start_time=start_time,
            )
        else:
            return self._make_result(
                success=False,
                error=error,
                error_code="BACKEND_ERROR",
                message=f"考试 {exam_id} 统计查询失败: {error}",
                trace_id=trace_id,
                start_time=start_time,
            )


# ============================================================
# 考试列表查询工具
# ============================================================

class ListExamsTool(BaseTool):
    """获取考试列表"""

    name = "list_exams"
    description = "获取考试列表，支持状态筛选和分页。返回考试的基本信息。"
    safety_level = "readonly"

    parameters = [
        ToolParameter(
            name="status",
            type="string",
            description="考试状态筛选：draft/published/closed",
            required=False,
            enum=["draft", "published", "closed"],
        ),
        ToolParameter(
            name="page",
            type="integer",
            description="页码，默认1",
            required=False,
            default=1,
        ),
        ToolParameter(
            name="page_size",
            type="integer",
            description="每页数量，默认20",
            required=False,
            default=20,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._client = BackendClient()

    async def execute(
        self,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        start_time = __import__("time").time()

        query_params = {}
        if "status" in params:
            query_params["status"] = params["status"]
        if "page" in params:
            query_params["page"] = params["page"]
        if "page_size" in params:
            query_params["page_size"] = params["page_size"]

        success, data, error = await self._client.get(
            "/exams/",
            user_id=user_id,
            role=role,
            params=query_params,
            trace_id=trace_id,
        )

        if success:
            return self._make_result(
                success=True,
                data=data,
                trace_id=trace_id,
                start_time=start_time,
            )
        else:
            return self._make_result(
                success=False,
                error=error,
                error_code="BACKEND_ERROR",
                trace_id=trace_id,
                start_time=start_time,
            )


# ============================================================
# 考试详情查询工具
# ============================================================

class GetExamDetailTool(BaseTool):
    """获取考试详情"""

    name = "get_exam_detail"
    description = "获取指定考试的详细信息，包括基本信息、题目数量等。"
    safety_level = "readonly"

    parameters = [
        ToolParameter(
            name="exam_id",
            type="integer",
            description="考试 ID",
            required=True,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._client = BackendClient()

    async def execute(
        self,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        start_time = __import__("time").time()
        exam_id = params["exam_id"]

        success, data, error = await self._client.get(
            f"/exams/{exam_id}",
            user_id=user_id,
            role=role,
            trace_id=trace_id,
        )

        if success:
            return self._make_result(
                success=True,
                data=data,
                trace_id=trace_id,
                start_time=start_time,
            )
        else:
            return self._make_result(
                success=False,
                error=error,
                error_code="BACKEND_ERROR",
                trace_id=trace_id,
                start_time=start_time,
            )


# ============================================================
# 考试统计分析工具
# ============================================================

class GetExamAnalysisTool(BaseTool):
    """获取考试统计分析"""

    name = "get_exam_analysis"
    description = "获取指定考试的完整分析数据，包括基础信息、统计信息（参与人数、平均分、通过率等）和答题概况。"
    safety_level = "readonly"

    parameters = [
        ToolParameter(
            name="exam_id",
            type="integer",
            description="考试 ID",
            required=True,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._client = BackendClient()

    async def execute(
        self,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        start_time = __import__("time").time()
        exam_id = params["exam_id"]

        success, data, error = await self._client.get(
            f"/exams/{exam_id}/analysis",
            user_id=user_id,
            role=role,
            trace_id=trace_id,
        )

        if success:
            return self._make_result(
                success=True,
                data=data,
                trace_id=trace_id,
                start_time=start_time,
            )
        else:
            return self._make_result(
                success=False,
                error=error,
                error_code="BACKEND_ERROR",
                trace_id=trace_id,
                start_time=start_time,
            )


# ============================================================
# 考试成绩列表工具
# ============================================================

class GetExamResultsTool(BaseTool):
    """获取考试成绩列表"""

    name = "get_exam_results"
    description = "获取指定考试的成绩列表，包含候选人得分、评分状态等信息。"
    safety_level = "readonly"

    parameters = [
        ToolParameter(
            name="exam_id",
            type="integer",
            description="考试 ID",
            required=True,
        ),
        ToolParameter(
            name="page",
            type="integer",
            description="页码，默认1",
            required=False,
            default=1,
        ),
        ToolParameter(
            name="page_size",
            type="integer",
            description="每页数量，默认20",
            required=False,
            default=20,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._client = BackendClient()

    async def execute(
        self,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        start_time = __import__("time").time()
        exam_id = params["exam_id"]

        query_params = {}
        if "page" in params:
            query_params["page"] = params["page"]
        if "page_size" in params:
            query_params["page_size"] = params["page_size"]

        success, data, error = await self._client.get(
            f"/exams/{exam_id}/results",
            user_id=user_id,
            role=role,
            params=query_params,
            trace_id=trace_id,
        )

        if success:
            return self._make_result(
                success=True,
                data=data,
                trace_id=trace_id,
                start_time=start_time,
            )
        else:
            return self._make_result(
                success=False,
                error=error,
                error_code="BACKEND_ERROR",
                trace_id=trace_id,
                start_time=start_time,
            )


# ============================================================
# 报告列表查询工具
# ============================================================

class ListReportsTool(BaseTool):
    """获取 AI 报告列表"""

    name = "list_reports"
    description = "获取 AI 分析报告列表，支持按考试 ID 和状态筛选。"
    safety_level = "readonly"

    parameters = [
        ToolParameter(
            name="exam_id",
            type="integer",
            description="考试 ID（可选筛选）",
            required=False,
        ),
        ToolParameter(
            name="status",
            type="string",
            description="报告状态筛选",
            required=False,
        ),
        ToolParameter(
            name="page",
            type="integer",
            description="页码，默认1",
            required=False,
            default=1,
        ),
        ToolParameter(
            name="page_size",
            type="integer",
            description="每页数量，默认20",
            required=False,
            default=20,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._client = BackendClient()

    async def execute(
        self,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        start_time = __import__("time").time()

        query_params = {}
        if "exam_id" in params:
            query_params["exam_id"] = params["exam_id"]
        if "status" in params:
            query_params["status"] = params["status"]
        if "page" in params:
            query_params["page"] = params["page"]
        if "page_size" in params:
            query_params["page_size"] = params["page_size"]

        success, data, error = await self._client.get(
            "/reports/",
            user_id=user_id,
            role=role,
            params=query_params,
            trace_id=trace_id,
        )

        if success:
            return self._make_result(
                success=True,
                data=data,
                trace_id=trace_id,
                start_time=start_time,
            )
        else:
            return self._make_result(
                success=False,
                error=error,
                error_code="BACKEND_ERROR",
                trace_id=trace_id,
                start_time=start_time,
            )


# ============================================================
# 报告详情查询工具
# ============================================================

class GetReportDetailTool(BaseTool):
    """获取 AI 报告详情"""

    name = "get_report_detail"
    description = "获取指定 AI 报告的详细内容，包括综合评价、优势、薄弱环节、技能分析等。"
    safety_level = "readonly"

    parameters = [
        ToolParameter(
            name="report_id",
            type="integer",
            description="报告 ID",
            required=True,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._client = BackendClient()

    async def execute(
        self,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        start_time = __import__("time").time()
        report_id = params["report_id"]

        success, data, error = await self._client.get(
            f"/reports/{report_id}",
            user_id=user_id,
            role=role,
            trace_id=trace_id,
        )

        if success:
            return self._make_result(
                success=True,
                data=data,
                trace_id=trace_id,
                start_time=start_time,
            )
        else:
            return self._make_result(
                success=False,
                error=error,
                error_code="BACKEND_ERROR",
                trace_id=trace_id,
                start_time=start_time,
            )


# ============================================================
# 候选人历史查询工具
# ============================================================

class GetCandidateHistoryTool(BaseTool):
    """获取候选人历史考试记录"""

    name = "get_candidate_history"
    description = "获取指定候选人的历史考试记录，包括考试名称、成绩、通过率等。"
    safety_level = "readonly"

    parameters = [
        ToolParameter(
            name="candidate_id",
            type="integer",
            description="候选人 ID",
            required=True,
        ),
        ToolParameter(
            name="page",
            type="integer",
            description="页码，默认1",
            required=False,
            default=1,
        ),
        ToolParameter(
            name="page_size",
            type="integer",
            description="每页数量，默认20",
            required=False,
            default=20,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._client = BackendClient()

    async def execute(
        self,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        start_time = __import__("time").time()
        candidate_id = params["candidate_id"]

        query_params = {}
        if "page" in params:
            query_params["page"] = params["page"]
        if "page_size" in params:
            query_params["page_size"] = params["page_size"]

        success, data, error = await self._client.get(
            f"/candidates/{candidate_id}/exam-history",
            user_id=user_id,
            role=role,
            params=query_params,
            trace_id=trace_id,
        )

        if success:
            return self._make_result(
                success=True,
                data=data,
                trace_id=trace_id,
                start_time=start_time,
            )
        else:
            return self._make_result(
                success=False,
                error=error,
                error_code="BACKEND_ERROR",
                trace_id=trace_id,
                start_time=start_time,
            )


# ============================================================
# 模板列表查询工具
# ============================================================

class ListTemplatesTool(BaseTool):
    """获取试卷模板列表"""

    name = "list_templates"
    description = "获取试卷模板列表，支持状态筛选和关键词搜索。"
    safety_level = "readonly"

    parameters = [
        ToolParameter(
            name="status",
            type="string",
            description="模板状态筛选",
            required=False,
        ),
        ToolParameter(
            name="keyword",
            type="string",
            description="关键词搜索",
            required=False,
        ),
        ToolParameter(
            name="page",
            type="integer",
            description="页码，默认1",
            required=False,
            default=1,
        ),
        ToolParameter(
            name="page_size",
            type="integer",
            description="每页数量，默认20",
            required=False,
            default=20,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._client = BackendClient()

    async def execute(
        self,
        params: dict[str, Any],
        user_id: int,
        role: str,
        trace_id: str | None = None,
    ) -> ToolResult:
        start_time = __import__("time").time()

        query_params = {}
        if "status" in params:
            query_params["status"] = params["status"]
        if "keyword" in params:
            query_params["keyword"] = params["keyword"]
        if "page" in params:
            query_params["page"] = params["page"]
        if "page_size" in params:
            query_params["page_size"] = params["page_size"]

        success, data, error = await self._client.get(
            "/templates/",
            user_id=user_id,
            role=role,
            params=query_params,
            trace_id=trace_id,
        )

        if success:
            return self._make_result(
                success=True,
                data=data,
                trace_id=trace_id,
                start_time=start_time,
            )
        else:
            return self._make_result(
                success=False,
                error=error,
                error_code="BACKEND_ERROR",
                trace_id=trace_id,
                start_time=start_time,
            )


# ============================================================
# 便捷方法：注册所有考试工具
# ============================================================

def register_exam_tools(registry) -> None:
    """注册所有考试相关工具到注册表（S5.2 更新）"""
    tools = [
        # S5.2 首批工具
        GetExamStatisticsTool(),      # 考试统计查询
        GetExamResultsTool(),         # 考试成绩查询
        GetCandidateHistoryTool(),    # 候选人考试历史查询
        # S5.1 基础工具
        ListExamsTool(),
        GetExamDetailTool(),
        GetExamAnalysisTool(),
        ListReportsTool(),
        GetReportDetailTool(),
        ListTemplatesTool(),
    ]
    for tool in tools:
        registry.register(tool)
