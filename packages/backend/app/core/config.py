"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "PRANELY API"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str  # Must be set in environment
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # Database
    DATABASE_URL: str  # Must be set in environment
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Canonical singleton instance for use throughout the application
settings = get_settings()