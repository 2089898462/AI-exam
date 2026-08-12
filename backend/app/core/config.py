"""
应用配置管理

安全敏感配置（JWT密钥、数据库密码、API Key）必须通过环境变量或 .env 文件配置。
禁止在代码中硬编码生产环境凭据。
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI考试系统（企业内部版）"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库配置（必须通过 .env 或环境变量覆盖）
    DATABASE_URL: str = ""

    # JWT 配置（必须通过 .env 或环境变量覆盖）
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # AI-Service 配置
    AI_SERVICE_URL: str = "http://localhost:8001"
    AI_SERVICE_TIMEOUT: float = 30.0

    # 安全配置
    SECURITY_PASSWORD_MIN_LENGTH: int = 8
    SECURITY_LOGIN_MAX_ATTEMPTS: int = 5
    SECURITY_LOGIN_LOCKOUT_MINUTES: int = 15

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
