# core/config.py - Completely fixed version
import os
import json
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Unknown Verdict v41.0"
    APP_VERSION: str = "41.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field("redis://localhost:6379", env="REDIS_URL")

    # Secrets
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # LLM Providers
    SARVAM_API_KEY: Optional[str] = Field(None, env="SARVAM_API_KEY")
    SARVAM_BASE_URL: str = "https://api.sarvam.ai"
    SARVAM_MODEL_105B: str = "sarvam-105b"
    SARVAM_MODEL_30B: str = "sarvam-30b"

    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4"

    GEMINI_API_KEY: Optional[str] = Field(None, env="GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-pro"

    GROQ_API_KEY: Optional[str] = Field(None, env="GROQ_API_KEY")
    GROQ_MODEL: str = "llama2-70b"

    DEEPSEEK_API_KEY: Optional[str] = Field(None, env="DEEPSEEK_API_KEY")
    DEEPSEEK_MODEL: str = "deepseek-chat"

    OPENROUTER_API_KEY: Optional[str] = Field(None, env="OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "meta-llama/llama-3-70b-instruct"

    # Moat configuration
    MOAT_ENABLED: bool = True
    MOAT_UPDATE_INTERVAL: int = 3600

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # Features
    ENABLE_STREAMING: bool = True
    ENABLE_CACHING: bool = True
    ENABLE_AUTH: bool = True

    # JSON fields - use string with custom parser
    TARGETED_SEARCH_DOMAINS: str = Field(
        default='["https://www.indiacode.nic.in", "https://www.sci.gov.in", "https://legalaffairs.gov.in"]',
        env="TARGETED_SEARCH_DOMAINS"
    )
    
    ALLOWED_ORIGINS: str = Field(
        default='["*"]',
        env="ALLOWED_ORIGINS"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

    def get_targeted_search_domains(self) -> List[str]:
        """Parse TARGETED_SEARCH_DOMAINS safely"""
        try:
            if not self.TARGETED_SEARCH_DOMAINS:
                return ["https://www.indiacode.nic.in", "https://www.sci.gov.in"]
            
            # Try JSON parse
            parsed = json.loads(self.TARGETED_SEARCH_DOMAINS)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, str):
                return [parsed]
        except json.JSONDecodeError:
            # Try comma-separated
            if "," in self.TARGETED_SEARCH_DOMAINS:
                return [item.strip() for item in self.TARGETED_SEARCH_DOMAINS.split(",") if item.strip()]
            # Try single value
            if self.TARGETED_SEARCH_DOMAINS.strip():
                return [self.TARGETED_SEARCH_DOMAINS.strip()]
        
        # Default fallback
        return ["https://www.indiacode.nic.in", "https://www.sci.gov.in"]

    def get_allowed_origins(self) -> List[str]:
        """Parse ALLOWED_ORIGINS safely"""
        try:
            if not self.ALLOWED_ORIGINS:
                return ["*"]
            
            parsed = json.loads(self.ALLOWED_ORIGINS)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, str):
                return [parsed]
        except json.JSONDecodeError:
            if "," in self.ALLOWED_ORIGINS:
                return [item.strip() for item in self.ALLOWED_ORIGINS.split(",") if item.strip()]
            if self.ALLOWED_ORIGINS.strip():
                return [self.ALLOWED_ORIGINS.strip()]
        
        return ["*"]


# Singleton instance
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton with robust fallback"""
    global _settings_instance
    
    if _settings_instance is not None:
        return _settings_instance
    
    try:
        # Try normal loading
        _settings_instance = Settings()
        logger.info("✅ Settings loaded successfully from environment")
    except Exception as e:
        logger.warning(f"⚠️ Failed to load settings: {e}. Using fallback.")
        _settings_instance = create_fallback_settings()
    
    return _settings_instance


def create_fallback_settings() -> Settings:
    """Create settings with hardcoded fallback values"""
    try:
        # Try to get from environment first
        db_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/unknown_verdict")
        secret = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        
        # Create settings with fallback
        return Settings(
            DATABASE_URL=db_url,
            REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379"),
            SECRET_KEY=secret,
            TARGETED_SEARCH_DOMAINS='["https://www.indiacode.nic.in", "https://www.sci.gov.in"]',
            ALLOWED_ORIGINS='["*"]'
        )
    except Exception as e:
        logger.error(f"❌ Even fallback failed: {e}")
        # Ultimate fallback - create with minimal required fields
        return Settings(
            DATABASE_URL="postgresql://localhost:5432/unknown_verdict",
            SECRET_KEY="emergency-fallback-key-change-now"
        )


# Export settings instance
try:
    settings = get_settings()
    logger.info(f"✅ Unknown Verdict v{settings.APP_VERSION} configured")
    logger.info(f"   Environment: {settings.ENVIRONMENT}")
    logger.info(f"   Database: {settings.DATABASE_URL[:30]}...")
    logger.info(f"   Redis: {settings.REDIS_URL[:30]}...")
except Exception as e:
    logger.error(f"❌ Critical failure loading settings: {e}")
    # Create minimal settings to keep app running
    settings = Settings(
        DATABASE_URL=os.getenv("DATABASE_URL", "postgresql://localhost:5432/unknown_verdict"),
        SECRET_KEY=os.getenv("SECRET_KEY", "emergency-key")
    )


# Helper functions for other modules
def get_search_domains() -> List[str]:
    """Convenience function for other modules"""
    return settings.get_targeted_search_domains()


def get_origins() -> List[str]:
    """Convenience function for CORS"""
    return settings.get_allowed_origins()