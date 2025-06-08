"""Application configuration using Pydantic settings."""
import os
from enum import Enum
from functools import lru_cache
from typing import Any, List, Optional

from pydantic import Field, field_serializer, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    app_env: Environment = Field(default=Environment.DEVELOPMENT)
    app_name: str = Field(default="FastAPI DDD Template")
    debug: bool = Field(default=False)

    # API
    api_prefix: str = Field(default="/api/v1")

    # PostgreSQL
    postgres_user: str = Field(...)
    postgres_password: str = Field(...)
    postgres_db: str = Field(...)
    postgres_host: str = Field(...)
    postgres_port: int = Field(default=5432)
    postgres_pool_size: int = Field(default=20)
    postgres_max_overflow: int = Field(default=40)

    # Redis
    redis_host: str = Field(...)
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)
    redis_pool_size: int = Field(default=10)

    # External Services
    telegram_bot_token: str = Field(...)
    telegram_notification_chat_id: Optional[str] = Field(default=None)
    google_api_key: str = Field(...)

    # Consumer Configuration
    run_consumers_in_api: bool = Field(
        default=True,
        description="Whether to run consumers in the API process (for dev) or separately (for prod)",
    )

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Security - Store as string internally, parse to list
    cors_origins: str = Field(default="http://localhost:3000")

    # Rate Limiting
    rate_limit_requests: int = Field(default=100)
    rate_limit_period: int = Field(default=60)  # seconds

    @field_validator("debug", mode="before")
    @classmethod
    def set_debug(cls, v: Any, info) -> bool:
        """Set debug based on environment if not explicitly set."""
        if v is None:
            env = info.data.get("app_env", Environment.DEVELOPMENT)
            return env == Environment.DEVELOPMENT
        return v

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins if isinstance(self.cors_origins, list) else []

    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.app_env == Environment.STAGING


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
