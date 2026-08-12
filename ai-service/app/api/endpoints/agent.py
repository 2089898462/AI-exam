"""
AI Agent API 端点

提供 AI Agent 的对外服务接口：
- POST /agent/chat - AI 对话（接收用户消息，返回 AI 响应）
- GET /agent/conversations - 获取会话列表
- GET /agent/conversations/{id} - 获取会话详情
- DELETE /agent/conversations/{id} - 删除会话
- GET /agent/tools - 获取可用工具列表

安全设计：
- 所有请求必须携带用户身份（X-User-Id, X-User-Role）
- AI 调用通过工具注册表访问 Backend，不直接操作数据库
- 所有 AI 调用记录审计日志
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.conversation import Conversation, ConversationManager
from app.core.config import AIConfig
from app.llm.provider import ModelProvider, get_provider, LLMCallResult
from app.tools.tool_registry import ToolRegistry, get_tool_registry


router = APIRouter()

# 全局会话管理器
conversation_manager = ConversationManager()


# ============================================================
# 请求/响应模型
# ============================================================

class ChatRequest(BaseModel):
    """AI 对话请求"""
    message: str
    conversation_id: str | None = None  # 续聊时传入
    user_id: int | None = None  # 由中间件注入
    role: str | None = None  # 由中间件注入
    trace_id: str | None = None


class ChatResponse(BaseModel):
    """AI 对话响应"""
    conversation_id: str
    reply: str
    tool_calls: list[dict[str, Any]] = []
    trace_id: str | None = None
    metadata: dict[str, Any] = {}


class ConversationResponse(BaseModel):
    """会话响应"""
    conversation_id: str
    user_id: int
    role: str
    message_count: int
    created_at: float
    updated_at: float
    metadata: dict[str, Any] = {}


class ToolInfoResponse(BaseModel):
    """工具信息响应"""
    tools: list[dict[str, Any]]


# ============================================================
# 权限辅助
# ============================================================

def _extract_user(request: ChatRequest) -> tuple[int, str]:
    """从请求中提取用户信息（后续改为中间件注入）"""
    user_id = request.user_id or 0
    role = request.role or "hr"

    if user_id <= 0:
        raise HTTPException(status_code=401, detail="无效的用户身份")

    if role not in ("admin", "hr"):
        raise HTTPException(status_code=403, detail="仅 HR 和管理员可使用 AI Agent")

    return user_id, role


# ============================================================
# AI Agent 核心逻辑
# ============================================================

async def _process_chat(
    message: str,
    user_id: int,
    role: str,
    conversation_id: str | None = None,
    trace_id: str | None = None,
) -> ChatResponse:
    """处理 AI 对话

    流程：
    1. 获取或创建会话
    2. 构建 LLM 消息（含 System Prompt + 历史 + 用户消息）
    3. 调用 LLM（含工具选择）
    4. 如果 LLM 选择了工具，执行工具调用
    5. 汇总结果，生成最终响应
    6. 保存到会话
    """
    # 1. 获取或创建会话
    if conversation_id:
        conv = conversation_manager.get_conversation(conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        conv = conversation_manager.create_conversation(
            user_id=user_id,
            role=role,
            trace_id=trace_id,
        )

    # 2. 加载 System Prompt
    from app.core.config import load_prompt
    try:
        system_prompt = load_prompt("agent", "system_v1")
        system_content = system_prompt.template
    except FileNotFoundError:
        system_content = "你是企业内部 AI 考试助手。"

    # 3. 构建消息
    messages = []

    # System 消息
    messages.append({"role": "system", "content": system_content})

    # 历史消息（最近 10 轮）
    recent = conv.get_recent_messages(limit=20)
    messages.extend(recent)

    # 用户消息
    messages.append({"role": "user", "content": message})

    # 4. 获取工具列表
    registry = get_tool_registry()
    available_tools = registry.list_tools(user_id=user_id, role=role)

    # 5. 调用 LLM
    provider = get_provider()
    llm_result = await provider.chat(messages=messages, trace_id=trace_id)

    if not llm_result.success:
        error_msg = llm_result.error or "AI 服务调用失败"
        raise HTTPException(status_code=500, detail=f"AI 服务错误: {error_msg}")

    ai_content = llm_result.response.content if llm_result.response else ""

    # 6. 尝试提取工具调用（基于关键字检测，后续升级为 function calling）
    tool_calls = []
    tool_results = []

    # 简单工具提取：检查 AI 响应中是否包含工具调用意图
    tool_call_instructions = _extract_tool_intent(ai_content, available_tools)

    for tool_instruction in tool_call_instructions:
        tool_name = tool_instruction.get("name", "")
        tool_params = tool_instruction.get("params", {})

        if tool_name and registry.get_tool(tool_name):
            result = await registry.execute(
                tool_name=tool_name,
                params=tool_params,
                user_id=user_id,
                role=role,
                trace_id=trace_id,
            )
            tool_calls.append({
                "tool": tool_name,
                "params": tool_params,
                "success": result.success,
            })
            tool_results.append(result)

    # 7. 生成最终响应
    if tool_results:
        reply = _generate_reply_with_tools(ai_content, tool_results)
    else:
        reply = ai_content

    # 8. 保存会话
    conv.add_message("user", message)
    conv.add_message("assistant", reply, metadata={
        "tool_calls": tool_calls,
        "trace_id": trace_id,
    })

    return ChatResponse(
        conversation_id=conv.conversation_id,
        reply=reply,
        tool_calls=tool_calls,
        trace_id=trace_id,
        metadata={
            "message_count": len(conv.messages),
            "llm_latency_ms": llm_result.response.latency_ms if llm_result.response else 0,
        },
    )


def _extract_tool_intent(content: str, available_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 AI 响应中提取工具调用意图

    基于简单的关键字匹配，后续升级为 LLM Function Calling。
    """
    tool_intents = []

    # 检查每个工具的触发条件
    trigger_map = {
        "list_exams": ["考试列表", "有哪些考试", "考试有哪些", "list_exams"],
        "get_exam_detail": ["考试详情", "考试信息", "考试内容", "get_exam_detail"],
        "get_exam_analysis": ["考试分析", "考试统计", "考试情况", "分析报告", "get_exam_analysis"],
        "get_exam_results": ["考试成绩", "成绩列表", "考试结果", "get_exam_results"],
        "list_reports": ["报告列表", "AI 报告", "分析报告", "list_reports"],
        "get_report_detail": ["报告详情", "详细报告", "get_report_detail"],
        "get_candidate_history": ["候选人历史", "历史考试", "历史记录", "get_candidate_history"],
        "list_templates": ["模板列表", "试卷模板", "list_templates"],
    }

    content_lower = content.lower()

    for tool_name, triggers in trigger_map.items():
        if tool_name not in [t["name"] for t in available_tools]:
            continue
        for trigger in triggers:
            if trigger.lower() in content_lower:
                # 尝试从上下文中提取参数
                params = _extract_params_for_tool(content, tool_name)
                tool_intents.append({"name": tool_name, "params": params})
                break

    return tool_intents


def _extract_params_for_tool(content: str, tool_name: str) -> dict[str, Any]:
    """从 AI 响应中提取工具参数"""
    import re

    params = {}

    if tool_name in ("get_exam_detail", "get_exam_analysis", "get_exam_results"):
        # 尝试提取 exam_id
        match = re.search(r'考试[：:]\s*(\d+)', content) or re.search(r'exam[_\s]*id[：:]\s*(\d+)', content, re.IGNORECASE)
        if match:
            params["exam_id"] = int(match.group(1))
        else:
            # 默认不传，让 Agent 后续追问
            pass

    elif tool_name in ("get_report_detail",):
        match = re.search(r'报告[：:]\s*(\d+)', content) or re.search(r'report[_\s]*id[：:]\s*(\d+)', content, re.IGNORECASE)
        if match:
            params["report_id"] = int(match.group(1))

    elif tool_name in ("get_candidate_history",):
        match = re.search(r'候选人[：:]\s*(\d+)', content) or re.search(r'candidate[_\s]*id[：:]\s*(\d+)', content, re.IGNORECASE)
        if match:
            params["candidate_id"] = int(match.group(1))

    return params


def _generate_reply_withols(ai_content: str, tool_results: list) -> str:
    """结合工具结果生成最终回复"""
    parts = [ai_content, ""]

    for result in tool_results:
        if result.success:
            parts.append(f"📊 工具执行成功 ({result.tool_name}):")
            # 摘要化展示
            data_str = str(result.data)[:500]
            parts.append(f"   {data_str}")
        else:
            parts.append(f"⚠️ 工具执行失败 ({result.tool_name}): {result.error}")

    return "\n".join(parts)


# ============================================================
# API 端点
# ============================================================

@router.post("/chat", response_model=ChatResponse)
async def ai_chat(request: ChatRequest):
    """AI 对话接口

    用户发送消息，AI Agent 处理后返回响应。
    支持多轮对话（通过 conversation_id 关联）。
    """
    user_id, role = _extract_user(request)
    trace_id = request.trace_id or str(uuid.uuid4())

    try:
        response = await _process_chat(
            message=request.message,
            user_id=user_id,
            role=role,
            conversation_id=request.conversation_id,
            trace_id=trace_id,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Agent 错误: {str(e)}")


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    user_id: int,
    role: str,
):
    """获取用户的会话列表"""
    if role not in ("admin", "hr"):
        raise HTTPException(status_code=403, detail="无权限")

    convs = conversation_manager.get_user_conversations(user_id)
    return [
        ConversationResponse(
            conversation_id=c.conversation_id,
            user_id=c.user_id,
            role=c.role,
            message_count=len(c.messages),
            created_at=c.created_at,
            updated_at=c.updated_at,
            metadata=c.metadata,
        )
        for c in convs
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user_id: int,
    role: str,
):
    """获取会话详情"""
    conv = conversation_manager.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    if conv.user_id != user_id and role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此会话")

    return ConversationResponse(
        conversation_id=conv.conversation_id,
        user_id=conv.user_id,
        role=conv.role,
        message_count=len(conv.messages),
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        metadata=conv.metadata,
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: int,
    role: str,
):
    """删除会话"""
    conv = conversation_manager.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    if conv.user_id != user_id and role != "admin":
        raise HTTPException(status_code=403, detail="无权删除此会话")

    conversation_manager.delete_conversation(conversation_id)
    return {"status": "ok", "message": "会话已删除"}


@router.get("/tools", response_model=ToolInfoResponse)
async def list_available_tools(
    user_id: int,
    role: str,
):
    """获取 AI Agent 可用的工具列表"""
    registry = get_tool_registry()
    tools = registry.list_tools(user_id=user_id, role=role)
    return ToolInfoResponse(tools=tools)


@router.get("/health")
async def agent_health_check():
    """AI Agent 健康检查"""
    registry = get_tool_registry()
    provider = get_provider()

    tools = registry.get_all_tools()
    return {
        "status": "ok",
        "service": "ai-agent",
        "tools_count": len(tools),
        "provider": provider._config.MODEL_NAME if hasattr(provider, '_config') else "unknown",
    }
