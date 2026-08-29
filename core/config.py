import os
from pathlib import Path
from typing import List, Optional

class Config:
    # ============================================================
    # APP INFORMATION
    # ============================================================
    APP_NAME = os.getenv("APP_NAME", "Unknown Verdict")
    APP_VERSION = os.getenv("APP_VERSION", "43.0")
    APP_DESCRIPTION = os.getenv(
        "APP_DESCRIPTION",
        "530+ Agents · 114 Endpoints · 32.5M Vectors · Zero Data Retention · Third Eye AI · Shakti Judge"
    )
    PROJECT_NAME = os.getenv("PROJECT_NAME", "Unknown Verdict")
    API_V1_STR = os.getenv("API_V1_STR", "/api/v1")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # ============================================================
    # PATHS
    # ============================================================
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    MODELS_DIR = BASE_DIR / "models"
    STATIC_DIR = BASE_DIR / "static"
    LOGS_DIR = BASE_DIR / "logs"

    for dir_path in [DATA_DIR, MODELS_DIR, STATIC_DIR, LOGS_DIR]:
        dir_path.mkdir(exist_ok=True)

    # ============================================================
    # LLM CONFIGURATION
    # ============================================================
    LLM_MODE = os.getenv("LLM_MODE", "hybrid")  # "offline", "online", "hybrid"
    LLM_MODEL_NAME = os.getenv("LLM_MODEL", "LiquidAI/LFM2.5-2.6B")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "law-ai/InCaseLawBERT")
    DEVICE = os.getenv("DEVICE", "cpu")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

    # ============================================================
    # ONLINE LLM PROVIDERS (For fallback)
    # ============================================================
    ONLINE_PROVIDERS: List[str] = ["groq", "openai", "gemini", "deepseek", "openrouter", "ollama"]
    PRIMARY_PROVIDER = os.getenv("PRIMARY_PROVIDER", "groq")

    # ✅ ADD THIS – Alias for backward compatibility
    available_llm_providers = ONLINE_PROVIDERS

    # ============================================================
    # API KEYS
    # ============================================================
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

    # ============================================================
    # OLLAMA CONFIGURATION
    # ============================================================
    OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # ============================================================
    # DATABASE
    # ============================================================
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/unknown_verdict")
    DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
    DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", "30"))

    # ============================================================
    # RAG CONFIGURATION – 32.5M VECTORS
    # ============================================================
    ZVEC_PATH = DATA_DIR / "legal_vectors.zvec"
    METADATA_PATH = DATA_DIR / "metadata.json"
    GRAPH_PATH = DATA_DIR / "citation_graph.pkl"
    RAG_BACKEND = os.getenv("RAG_BACKEND", "zvec")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "10"))
    RAG_VECTOR_DIM = int(os.getenv("RAG_VECTOR_DIM", "768"))
    RAG_TOTAL_VECTORS = int(os.getenv("RAG_TOTAL_VECTORS", "32518048"))

    # ============================================================
    # ZERO DATA RETENTION
    # ============================================================
    ZERO_DATA_RETENTION = os.getenv("ZERO_DATA_RETENTION", "true").lower() == "true"
    RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "0"))
    ANONYMIZE_LOGS = os.getenv("ANONYMIZE_LOGS", "true").lower() == "true"

    # ============================================================
    # SECURITY & AUTH
    # ============================================================
    JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "10080"))
    JWT_REFRESH_EXPIRATION_DAYS = int(os.getenv("JWT_REFRESH_EXPIRATION_DAYS", "30"))

    # ============================================================
    # CORS
    # ============================================================
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    ALLOWED_HEADERS = ["*"]

    # ============================================================
    # FEATURE FLAGS
    # ============================================================
    ENABLE_AUDIO_AGENT = os.getenv("ENABLE_AUDIO_AGENT", "true").lower() == "true"
    ENABLE_GRAPH_RAG = os.getenv("ENABLE_GRAPH_RAG", "true").lower() == "true"
    ENABLE_AGENTIC_RAG = os.getenv("ENABLE_AGENTIC_RAG", "true").lower() == "true"
    ENABLE_THIRD_EYE = os.getenv("ENABLE_THIRD_EYE", "true").lower() == "true"
    ENABLE_MCP = os.getenv("ENABLE_MCP", "true").lower() == "true"
    ENABLE_MOAT = os.getenv("ENABLE_MOAT", "true").lower() == "true"
    ENABLE_JUDGE = os.getenv("ENABLE_JUDGE", "true").lower() == "true"
    ENABLE_VERIFIERS = os.getenv("ENABLE_VERIFIERS", "true").lower() == "true"
    ENABLE_ARTICLES = os.getenv("ENABLE_ARTICLES", "true").lower() == "true"
    ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
    ENABLE_TARGETED_SEARCH = os.getenv("ENABLE_TARGETED_SEARCH", "true").lower() == "true"

    # ============================================================
    # VERDICT ENGINE
    # ============================================================
    USE_VERDICT_ENGINE = os.getenv("USE_VERDICT_ENGINE", "true").lower() == "true"
    VERDICT_ENGINE_MODE = os.getenv("VERDICT_ENGINE_MODE", "balanced")

    # ============================================================
    # AGENTS CONFIGURATION – 530+ Agents
    # ============================================================
    TOTAL_AGENTS = int(os.getenv("TOTAL_AGENTS", "530"))
    AGENT_CATEGORIES = {
        "Lawyer": 100,
        "Journalist": 75,
        "Spiritual": 75,
        "Compliance": 80,
        "Contracts": 60,
        "AI & Tech": 60,
        "Digital": 40,
        "Litigation": 30,
        "Strategic": 10,
    }
    AGENT_JURISDICTIONS = ["India", "US", "UK", "EU"]

    # ============================================================
    # ENDPOINTS CONFIGURATION – 114 Endpoints
    # ============================================================
    TOTAL_ENDPOINTS = int(os.getenv("TOTAL_ENDPOINTS", "114"))
    PUBLIC_ENDPOINTS = int(os.getenv("PUBLIC_ENDPOINTS", "82"))
    MOAT_ENDPOINTS = int(os.getenv("MOAT_ENDPOINTS", "32"))

    # ============================================================
    # JURISDICTIONS
    # ============================================================
    JURISDICTIONS = ["India", "US", "UK", "EU", "Canada", "Australia", "Singapore", "UAE"]

    # ============================================================
    # RATE LIMITING
    # ============================================================
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    RATE_LIMIT_PER_MINUTE = RATE_LIMIT_REQUESTS
    RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "1000"))

    # ============================================================
    # CACHE
    # ============================================================
    REDIS_URL = os.getenv("REDIS_URL", "")
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
    CACHE_TTL_SECONDS = CACHE_TTL

    # ============================================================
    # LOGGING
    # ============================================================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    LOG_FILE = LOGS_DIR / "unknown_verdict.log"

    # ============================================================
    # THIRD EYE (Monitoring)
    # ============================================================
    THIRD_EYE_ENABLED = os.getenv("THIRD_EYE_ENABLED", "true").lower() == "true"
    THIRD_EYE_HEARTBEAT_INTERVAL = int(os.getenv("THIRD_EYE_HEARTBEAT_INTERVAL", "60"))

    # ============================================================
    # SHAKTI – The Final Judge
    # ============================================================
    JUDGE_NAME = os.getenv("JUDGE_NAME", "Shakti")
    JUDGE_VERSION = os.getenv("JUDGE_VERSION", "1.0")
    JUDGE_MIN_CONFIDENCE = float(os.getenv("JUDGE_MIN_CONFIDENCE", "0.6"))

    # ============================================================
    # HELPERS
    # ============================================================
    @classmethod
    def is_offline_ready(cls) -> bool:
        return cls.ZVEC_PATH.exists() and cls.METADATA_PATH.exists()

    @classmethod
    def is_redis_available(cls) -> bool:
        return bool(cls.REDIS_URL)

    @classmethod
    def get_agent_count(cls) -> int:
        return sum(cls.AGENT_CATEGORIES.values())

    @classmethod
    def get_endpoint_count(cls) -> int:
        return cls.TOTAL_ENDPOINTS


# ============================================================
# CREATE SETTINGS INSTANCE
# ============================================================
settings = Config()


# ============================================================
# EXPOSE FOR BACKWARD COMPATIBILITY
# ============================================================
__all__ = [
    "Config",
    "settings",
]