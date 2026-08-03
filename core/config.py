# core/config.py - Fixed version
import os
import json
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Unknown Verdict v41.0"
    APP_VERSION: str = "41.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field(..., env="REDIS_URL")

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

    # JSON fields - handle gracefully if not set
    TARGETED_SEARCH_DOMAINS: List[str] = Field(
        default_factory=lambda: [
            "https://www.indiacode.nic.in",
            "https://www.sci.gov.in",
            "https://legalaffairs.gov.in"
        ],
        env="TARGETED_SEARCH_DOMAINS"
    )

    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: ["*"],
        env="ALLOWED_ORIGINS"
    )

    # For backward compatibility with old JSON parsing
    @field_validator("TARGETED_SEARCH_DOMAINS", mode="before")
    @classmethod
    def parse_json_field(cls, v):
        """Parse JSON string or return default if invalid"""
        if v is None:
            return cls.model_fields["TARGETED_SEARCH_DOMAINS"].default
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                # If it's a single string, wrap in list
                if isinstance(parsed, str):
                    return [parsed]
            except json.JSONDecodeError:
                # If it's a comma-separated string, split it
                if "," in v:
                    return [item.strip() for item in v.split(",")]
                # Otherwise, return as single-item list
                return [v]
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_json_field_origins(cls, v):
        """Parse JSON string or return default if invalid"""
        if v is None:
            return ["*"]
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, str):
                    return [parsed]
            except json.JSONDecodeError:
                if "," in v:
                    return [item.strip() for item in v.split(",")]
                return [v]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance
_settings_instance: Optional[Settings] = None


def get_settings():
    """Get settings singleton with fallback defaults"""
    global _settings_instance
    if _settings_instance is None:
        try:
            _settings_instance = Settings()
        except Exception as e:
            # Fallback to using environment variables directly
            import logging
            logging.warning(f"Failed to load settings: {e}. Using fallback.")
            _settings_instance = create_fallback_settings()
    return _settings_instance


def create_fallback_settings():
    """Create settings with fallback values when env fails"""
    return Settings(
        DATABASE_URL=os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db"),
        REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379"),
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-key-change-me"),
        TARGETED_SEARCH_DOMAINS=["https://www.indiacode.nic.in"],
        ALLOWED_ORIGINS=["*"]
    )


# Export settings instance
settings = get_settings()