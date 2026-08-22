import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME = os.getenv("APP_NAME", "Unknown Verdict")
    APP_VERSION = os.getenv("APP_VERSION", "43.0")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    REDIS_URL = os.getenv("REDIS_URL", "")
    
    # LLM Providers
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    
    # Ollama (local)
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
    
    # Document Intelligence
    DOCUCHAT_ENABLED = os.getenv("DOCUCHAT_ENABLED", "true").lower() == "true"
    DOCUCHAT_MODEL = os.getenv("DOCUCHAT_MODEL", "qwen2.5:3b")
    
    # LQ.AI Citation Engine
    LQAI_ENABLED = os.getenv("LQAI_ENABLED", "true").lower() == "true"
    LQAI_HOST = os.getenv("LQAI_HOST", "http://localhost:8000")
    
    # Security
    JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production")
    ZERO_DATA_RETENTION = os.getenv("ZERO_DATA_RETENTION", "true").lower() == "true"
    
    # Features
    USE_VERDICT_ENGINE = os.getenv("USE_VERDICT_ENGINE", "true").lower() == "true"
    VERDICT_ENGINE_MODE = os.getenv("VERDICT_ENGINE_MODE", "balanced")
    ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
    ENABLE_TARGETED_SEARCH = os.getenv("ENABLE_TARGETED_SEARCH", "true").lower() == "true"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    
    # Cache
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def available_llm_providers(self) -> List[str]:
        providers = []
        if self.GROQ_API_KEY: providers.append("groq")
        if self.OPENAI_API_KEY: providers.append("openai")
        if self.GEMINI_API_KEY: providers.append("gemini")
        if self.DEEPSEEK_API_KEY: providers.append("deepseek")
        if self.OPENROUTER_API_KEY: providers.append("openrouter")
        if self.OLLAMA_ENABLED: providers.append("ollama")
        return providers

settings = Settings()