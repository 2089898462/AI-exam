"""
应用配置管理
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "企业AI智能考试与能力评估系统"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/exam_system"

    # JWT 配置（安全敏感，必须通过环境变量覆盖）
    JWT_SECRET_KEY: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
