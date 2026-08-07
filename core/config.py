from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Unknown Verdict"
    APP_VERSION: str = "43.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    
    # JWT Settings - Use your existing HF Secret
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET", os.getenv("JWR_SECRET", "fallback-secret-key-change-me"))
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
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
    
    # Rate Limiting
    RATE_LIMIT_WINDOW: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 100
    
    # Admin
    ADMIN_SECRET: Optional[str] = os.getenv("ADMIN_SECRET")
    ADMIN_KEY: Optional[str] = os.getenv("ADMIN_KEY")
    
    # Search
    ENABLE_WEB_SEARCH: bool = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"
    ENABLE_TARGETED_SEARCH: bool = os.getenv("ENABLE_TARGETED_SEARCH", "false").lower() == "true"
    TARGETED_SEARCH_DOMAINS: Optional[str] = os.getenv("TARGETED_SEARCH_DOMAINS")
    SERPAPI_KEY: Optional[str] = os.getenv("SERPAPI_KEY")
    
    # Other
    VERDICT_ENGINE_MODE: str = os.getenv("VERDICT_ENGINE_MODE", "standard")
    USE_VERDICT_ENGINE: bool = os.getenv("USE_VERDICT_ENGINE", "true").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

def is_reddit_available() -> bool:
    """Check if Reddit API credentials are available"""
    return bool(settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_ID != "")

def get_llm_providers() -> dict:
    """Get available LLM providers"""
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