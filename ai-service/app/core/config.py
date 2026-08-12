"""
AI-Service 配置管理
加载模型配置和 Prompt 模板

安全说明：
- API_KEY 必须通过环境变量或 .env 文件配置
- 禁止在代码中硬编码生产 API Key
"""
import os
from pathlib import Path

import yaml
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载 ai-service/.env 文件
load_dotenv()


# ============================================================
# 模型配置
# ============================================================

class AIConfig:
    """AI 服务配置

    敏感配置通过环境变量或 .env 文件覆盖，禁止硬编码。
    支持多 Provider：deepseek / dashscope / openai / anthropic

    所有属性通过 @property 实现动态读取环境变量，
    确保运行时修改环境变量后配置立即生效。
    """

    # 默认值常量
    _DEFAULT_MODEL_NAME = "deepseek-v4-flash"
    _DEFAULT_MODEL_PROVIDER = "deepseek"
    _DEFAULT_API_BASE = "https://api.deepseek.com/v1"
    _DEFAULT_MAX_TOKENS = "2048"
    _DEFAULT_TEMPERATURE = "0.3"
    _DEFAULT_SERVICE_HOST = "0.0.0.0"
    _DEFAULT_SERVICE_PORT = "8001"
    _DEFAULT_REQUEST_TIMEOUT = "30.0"

    @property
    def MODEL_NAME(self) -> str:
        return os.environ.get("AI_MODEL_NAME", self._DEFAULT_MODEL_NAME)

    @property
    def MODEL_PROVIDER(self) -> str:
        return os.environ.get("AI_MODEL_PROVIDER", self._DEFAULT_MODEL_PROVIDER)

    @property
    def API_KEY(self) -> str:
        return os.environ.get("AI_API_KEY", "")

    @property
    def API_BASE(self) -> str:
        return os.environ.get("AI_API_BASE", self._DEFAULT_API_BASE)

    @property
    def MAX_TOKENS(self) -> int:
        return int(os.environ.get("AI_MAX_TOKENS", self._DEFAULT_MAX_TOKENS))

    @property
    def TEMPERATURE(self) -> float:
        return float(os.environ.get("AI_TEMPERATURE", self._DEFAULT_TEMPERATURE))

    @property
    def SERVICE_HOST(self) -> str:
        return os.environ.get("AI_SERVICE_HOST", self._DEFAULT_SERVICE_HOST)

    @property
    def SERVICE_PORT(self) -> int:
        return int(os.environ.get("AI_SERVICE_PORT", self._DEFAULT_SERVICE_PORT))

    @property
    def REQUEST_TIMEOUT(self) -> float:
        return float(os.environ.get("AI_REQUEST_TIMEOUT", self._DEFAULT_REQUEST_TIMEOUT))


# 单例配置实例
config = AIConfig()


def validate_ai_config() -> list[str]:
    """验证 AI 服务安全配置"""
    warnings: list[str] = []

    if not config.API_KEY:
        warnings.append(
            "[SECURITY] AI_API_KEY 未配置！"
            "必须通过环境变量或 .env 文件设置 API Key。"
        )

    return warnings


# ============================================================
# Prompt 加载器
# ============================================================

PROMPT_BASE_PATH = Path(__file__).parent.parent / "prompts"


class PromptConfig(BaseModel):
    """Prompt 配置结构"""
    version: str
    description: str = ""
    input: list[str] = []
    output: list[str] | dict[str, str] = []
    template: str


def load_prompt(prompt_type: str, version: str = "v1") -> PromptConfig:
    """加载 Prompt 模板配置

    Args:
        prompt_type: Prompt 类型 (scoring, report)
        version: 版本号

    Returns:
        PromptConfig: Prompt 配置对象

    Raises:
        FileNotFoundError: Prompt 文件不存在
        ValueError: Prompt 配置格式错误
    """
    prompt_path = PROMPT_BASE_PATH / prompt_type / f"{version}.yaml"

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "template" not in data:
        raise ValueError(f"Prompt 配置格式错误: {prompt_path}")

    return PromptConfig(
        version=data.get("version", "1.0"),
        description=data.get("description", ""),
        input=data.get("input", []),
        output=data.get("output", {}),
        template=data["template"],
    )


def render_prompt(prompt: PromptConfig, **kwargs) -> str:
    """渲染 Prompt 模板

    Args:
        prompt: Prompt 配置
        **kwargs: 模板变量

    Returns:
        str: 渲染后的 Prompt
    """
    try:
        return prompt.template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Prompt 模板变量缺失: {e}")
