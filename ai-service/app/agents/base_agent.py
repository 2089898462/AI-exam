"""
AI Agent 基础接口
定义所有 Agent 必须实现的标准接口
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """AI Agent 基类"""

    @abstractmethod
    async def run(self, **kwargs) -> dict[str, Any]:
        """执行 Agent 核心逻辑"""
        ...

    @abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """校验输入参数"""
        ...
