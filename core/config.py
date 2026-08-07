from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import field_validator
import os

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Unknown Verdict"
    APP_VERSION: str = "43.0"
    DEBUG: bool = True  # ← FIXED: True not true
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    
    # JWT Settings
    jwt_signing_key: str = os.getenv("JWT_SECRET", os.getenv("JWR_SECRET", "fallback-secret-key-change-me"))
    
    # Admin Keys
    admin_keys: List[str] = [os.getenv("ADMIN_KEY", ""), os.getenv("ADMIN_SECRET", "")]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    CACHE_PREFIX: str = "unknown_verdict:"
    
    # LLM Providers
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    SARVAM_API_KEY: Optional[str] = os.getenv("SARVAM_API_KEY")
    
    # DeepSeek Configuration
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # OpenRouter Configuration
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "openai/gpt-3.5-turbo"
    OPENROUTER_REFERRER: str = "https://upamnyu12-lex.hf.space"
    
    # Reddit (Optional)
    REDDIT_CLIENT_ID: Optional[str] = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: Optional[str] = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT: str = "UnknownVerdict/1.0"
    
    # Legal Intelligence
    LEGAL_INTELLIGENCE_ENABLED: bool = True
    MAX_CONTENT_PER_SOURCE: int = 50
    MIN_LEGAL_RELEVANCE: float = 0.3
    
    # Search
    ENABLE_WEB_SEARCH: bool = False
    ENABLE_TARGETED_SEARCH: bool = False
    TARGETED_SEARCH_DOMAINS: Optional[str] = os.getenv("TARGETED_SEARCH_DOMAINS")
    SERPAPI_KEY: Optional[str] = os.getenv("SERPAPI_KEY")
    
    # Verdict Engine
    VERDICT_ENGINE_MODE: str = os.getenv("VERDICT_ENGINE_MODE", "standard")
    USE_VERDICT_ENGINE: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False

    # Validators for boolean fields
    @field_validator('ENABLE_WEB_SEARCH', 'ENABLE_TARGETED_SEARCH', 'USE_VERDICT_ENGINE', 'DEBUG', mode='before')
    @classmethod
    def coerce_bool(cls, v):
        """Strip whitespace/newlines and parse common boolean strings."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            cleaned = v.strip().lower()
            if cleaned in ['true', '1', 'yes', 'on', 't', 'y']:
                return True
            if cleaned in ['false', '0', 'no', 'off', 'f', 'n', '']:
                return False
        return False

# Create settings instance
settings = Settings()

def is_reddit_available() -> bool:
    return bool(settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_ID != "")

def get_llm_providers() -> dict:
    providers = {}
    if settings.GROQ_API_KEY:
        providers["groq"] = settings.GROQ_API_KEY
    if settings.OPENAI_API_KEY:
        providers["openai"] = settings.OPENAI_API_KEY
    if settings.GEMINI_API_KEY:
        providers["gemini"] = settings.GEMINI_API_KEY
    if settings.DEEPSEEK_API_KEY:
        providers["deepseek"] = {
            "api_key": settings.DEEPSEEK_API_KEY,
            "base_url": settings.DEEPSEEK_BASE_URL
        }
    if settings.OPENROUTER_API_KEY:
        providers["openrouter"] = settings.OPENROUTER_API_KEY
    if settings.SARVAM_API_KEY:
        providers["sarvam"] = settings.SARVAM_API_KEY
    return providers