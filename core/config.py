import os
from pathlib import Path
from typing import List, Optional

class Config:
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    MODELS_DIR = BASE_DIR / "models"
    STATIC_DIR = BASE_DIR / "static"

    DATA_DIR.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(exist_ok=True)

    # LLM Configuration
    LLM_MODE = os.getenv("LLM_MODE", "hybrid")  # "offline", "online", "hybrid"
    LLM_MODEL_NAME = os.getenv("LLM_MODEL", "LiquidAI/LFM2.5-2.6B")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "law-ai/InCaseLawBERT")
    DEVICE = os.getenv("DEVICE", "cpu")  # "cpu" or "cuda"

    # RAG Configuration
    ZVEC_PATH = DATA_DIR / "legal_vectors.zvec"
    METADATA_PATH = DATA_DIR / "metadata.json"
    GRAPH_PATH = DATA_DIR / "citation_graph.pkl"
    RAG_BACKEND = os.getenv("RAG_BACKEND", "zvec")  # "zvec", "faiss", "hybrid"

    # Online Providers (fallback)
    ONLINE_PROVIDERS: List[str] = ["groq", "openai", "gemini", "deepseek", "openrouter"]
    PRIMARY_PROVIDER = os.getenv("PRIMARY_PROVIDER", "groq")

    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/unknown_verdict")

    # Zero Data Retention
    ZERO_DATA_RETENTION = True
    RETENTION_DAYS = 0  # Delete immediately

    # Security
    JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_MINUTES = 60 * 24 * 7

    # CORS
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

    # Feature Flags
    ENABLE_AUDIO_AGENT = os.getenv("ENABLE_AUDIO_AGENT", "true").lower() == "true"
    ENABLE_GRAPH_RAG = os.getenv("ENABLE_GRAPH_RAG", "true").lower() == "true"
    ENABLE_AGENTIC_RAG = os.getenv("ENABLE_AGENTIC_RAG", "true").lower() == "true"
    ENABLE_THIRD_EYE = os.getenv("ENABLE_THIRD_EYE", "true").lower() == "true"
    ENABLE_MCP = os.getenv("ENABLE_MCP", "true").lower() == "true"
    ENABLE_MOAT = os.getenv("ENABLE_MOAT", "true").lower() == "true"

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def is_offline_ready(cls) -> bool:
        """Check if offline components are available."""
        return cls.ZVEC_PATH.exists() and cls.METADATA_PATH.exists()