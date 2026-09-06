"""Centralised settings — all configuration from environment variables."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "changeme"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # JWT
    JWT_SECRET_KEY: str = "changeme-jwt"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "exam_guardian"
    DB_USER: str = "root"
    DB_PASSWORD: str = "changeme"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Groq (PRIMARY AI)
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama3-8b-8192"
    GROQ_TIMEOUT_SECONDS: int = 30
    GROQ_MAX_RETRIES: int = 2

    # NVIDIA NIM (FALLBACK AI)
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "meta/llama3-8b-instruct"
    NVIDIA_TIMEOUT_SECONDS: int = 30
    NVIDIA_MAX_RETRIES: int = 2

    # MCP Server
    MCP_HOST: str = "mcp"
    MCP_PORT: int = 8001
    MCP_SECRET: str = "changeme-mcp"

    # RAG Engine
    RAG_HOST: str = "rag"
    RAG_PORT: int = 8002

    # CORS
    CORS_ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60

    # Risk Engine weights (all configurable)
    RISK_WEIGHT_TAB_SWITCH: int = 10
    RISK_WEIGHT_FOCUS_LOSS: int = 5
    RISK_WEIGHT_COPY: int = 15
    RISK_WEIGHT_PASTE: int = 15
    RISK_WEIGHT_FULLSCREEN_EXIT: int = 10
    RISK_WEIGHT_SUSPICIOUS_NAVIGATION: int = 20
    RISK_WEIGHT_AI_ASSISTANT_SIGNAL: int = 25
    RISK_WEIGHT_REPEATED_VIOLATIONS: int = 20
    RISK_WEIGHT_SUSPICIOUS_SEQUENCE: int = 20

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"mysql+mysqldb://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
