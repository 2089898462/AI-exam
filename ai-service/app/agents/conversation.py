"""
会话管理模块

提供 AI Agent 会话基础能力：
- 会话 ID 生成与管理
- 会话消息记录
- 用户关联
- 上下文维护

注意：不保存敏感数据（密码、Token、完整用户数据等）
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationMessage:
    """会话消息"""
    role: str  # user / assistant / system / tool
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class Conversation:
    """AI 会话"""
    conversation_id: str
    user_id: int
    role: str  # 用户角色（admin/hr/candidate）
    trace_id: str | None = None
    messages: list[ConversationMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        user_id: int,
        role: str,
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Conversation":
        """创建新会话"""
        return cls(
            conversation_id=str(uuid.uuid4()),
            user_id=user_id,
            role=role,
            trace_id=trace_id,
            metadata=metadata or {},
        )

    def add_message(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage:
        """添加消息"""
        msg = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(msg)
        self.updated_at = time.time()
        return msg

    def get_recent_messages(self, limit: int = 20) -> list[dict[str, Any]]:
        """获取最近 N 条消息（供 LLM 使用）"""
        recent = self.messages[-limit:]
        return [
            {"role": m.role, "content": m.content}
            for m in recent
            if m.role in ("user", "assistant", "system")
        ]

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典（不包含完整消息历史，避免过大）"""
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "role": self.role,
            "trace_id": self.trace_id,
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


class ConversationManager:
    """会话管理器（内存实现，后续可扩展为 Redis/数据库）"""

    def __init__(self, max_conversations: int = 1000):
        self._conversations: dict[str, Conversation] = {}
        self._max_conversations = max_conversations

    def create_conversation(
        self,
        user_id: int,
        role: str,
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """创建新会话"""
        conv = Conversation.create(
            user_id=user_id,
            role=role,
            trace_id=trace_id,
            metadata=metadata,
        )
        self._evict_if_needed()
        self._conversations[conv.conversation_id] = conv
        return conv

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """获取会话"""
        return self._conversations.get(conversation_id)

    def get_user_conversations(self, user_id: int) -> list[Conversation]:
        """获取用户的所有会话"""
        return [
            c for c in self._conversations.values()
            if c.user_id == user_id
        ]

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationMessage | None:
        """向指定会话添加消息"""
        conv = self.get_conversation(conversation_id)
        if conv is None:
            return None
        return conv.add_message(role, content, metadata)

    def _evict_if_needed(self) -> None:
        """超过最大数量时移除最旧的会话"""
        if len(self._conversations) >= self._max_conversations:
            sorted_convs = sorted(
                self._conversations.values(),
                key=lambda c: c.updated_at,
            )
            for old_conv in sorted_convs[:len(self._conversations) - self._max_conversations + 1]:
                del self._conversations[old_conv.conversation_id]
