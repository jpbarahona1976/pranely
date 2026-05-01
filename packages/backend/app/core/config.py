"""Application configuration using Pydantic Settings.

FASE 8C.2 FIX: Secrets Validation - Validar secrets en producción
Raise HTTPException(500) si STRIPE_SECRET_KEY o STRIPE_WEBHOOK_SECRET faltantes en prod
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(Exception):
    """Raised when required configuration is missing in production."""
    pass


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "PRANELY API"
    DEBUG: bool = False
    ENV: str = "development"
    
    # Security
    SECRET_KEY: str  # Must be set in environment
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # Database
    DATABASE_URL: str  # Must be set in environment
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None  # Stripe API key for checkout sessions
    STRIPE_WEBHOOK_SECRET: Optional[str] = None  # Must be set for webhook verification
    
    # Frontend URL for redirects
    FRONTEND_URL: str = "http://localhost:3000"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra='ignore',
    )
    
    def validate_production_config(self) -> None:
        """
        FASE 8C.2 FIX: Validate required secrets for production.
        
        In production (ENV=production), raises ConfigurationError if
        Stripe secrets are missing. In development, logs warnings only.
        
        Raises:
            ConfigurationError: If required secrets are missing in production
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if self.ENV == "production":
            errors = []
            
            # Validate Stripe secret key
            if not self.STRIPE_SECRET_KEY:
                errors.append("STRIPE_SECRET_KEY is not set")
                logger.critical("STRIPE_SECRET_KEY missing in production!")
            
            # Validate Stripe webhook secret
            if not self.STRIPE_WEBHOOK_SECRET:
                errors.append("STRIPE_WEBHOOK_SECRET is not set")
                logger.critical("STRIPE_WEBHOOK_SECRET missing in production!")
            
            # Validate SECRET_KEY
            if not self.SECRET_KEY or self.SECRET_KEY == "changeme":
                errors.append("SECRET_KEY is not set or is placeholder")
                logger.critical("SECRET_KEY missing or placeholder in production!")
            
            if errors:
                error_msg = f"Configuration errors in production: {'; '.join(errors)}"
                logger.error(error_msg)
                raise ConfigurationError(error_msg)
        else:
            # Development mode - just warn
            if not self.STRIPE_SECRET_KEY:
                logger.warning(
                    "STRIPE_SECRET_KEY not set - Stripe checkout will use mock responses"
                )
            if not self.STRIPE_WEBHOOK_SECRET:
                logger.warning(
                    "STRIPE_WEBHOOK_SECRET not set - webhook signature verification disabled"
                )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def validate_settings() -> None:
    """
    FASE 8C.2 FIX: Validate settings for production readiness.
    
    Call this during application startup to ensure production
    configuration is complete. Raises ConfigurationError if validation fails.
    """
    settings = get_settings()
    settings.validate_production_config()


# Canonical singleton instance for use throughout the application
settings = get_settings()