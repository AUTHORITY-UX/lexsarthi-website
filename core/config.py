"""
core/config.py — Unknown Verdict v41.0
=======================================
FIX: This file was missing the `settings` object that app.py and other
modules import via `from core.config import settings`.

This file provides:
  1. `settings` — a Pydantic BaseSettings instance with ALL config fields
     (backward compatible with existing app.py imports)
  2. `LLM_ROUTING` — tiered routing table (simple→Groq, medium→30B, complex→105B)
  3. `classify_complexity()` — query complexity classifier
  4. All JWT, rate-limiting, Redis, and feature-flag config

DEPLOY: Replace core/config.py with this file.
       This supersedes config_updates.py — it includes everything from that file
       PLUS the `settings` object.

REQUIRES: pip install pydantic pydantic-settings
"""

from __future__ import annotations

import os
import logging
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Fallback for older pydantic
    try:
        from pydantic.v1 import BaseSettings
        SettingsConfigDict = dict
    except ImportError:
        # Last resort: use a plain class
        BaseSettings = object
        SettingsConfigDict = dict

logger = logging.getLogger("core.config")


# ════════════════════════════════════════════════════════════════════════
# SETTINGS — the main config object (imported as `from core.config import settings`)
# ════════════════════════════════════════════════════════════════════════
class Settings(BaseSettings):
    """Central configuration for Unknown Verdict v41.0."""

    if SettingsConfigDict is not dict:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            case_sensitive=False,
        )

    # ── App ──────────────────────────────────────────────────────
    app_name: str = "Unknown Verdict"
    version: str = "41.0"
    environment: str = "production"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 7860

    # ── Database (Neon PostgreSQL) ───────────────────────────────
    database_url: str = ""
    neon_database_url: str = ""
    db_pool_min: int = 2
    db_pool_max: int = 10
    db_command_timeout: int = 30

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = ""
    upstash_redis_url: str = ""
    cache_enabled: bool = True
    cache_ttl_hours: int = 24

    # ── JWT Auth ─────────────────────────────────────────────────
    jwt_secret: str = "unknown-verdict-dev-secret-change-in-production-please-set-a-real-key"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    enforce_auth: bool = False

    # ── Rate Limiting ────────────────────────────────────────────
    rate_limit_per_min: int = 100
    rate_limit_window: int = 60

    # ── LLM Providers ───────────────────────────────────────────
    sarvam_api_key: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    deepseek_api_key: str = ""
    openrouter_api_key: str = ""
    llm_providers: list[str] = ["sarvam", "openai", "gemini", "groq", "deepseek", "openrouter"]

    # ── Streaming / SSE ─────────────────────────────────────────
    enable_streaming: bool = True
    sse_heartbeat_interval: int = 15

    # ── Moat ─────────────────────────────────────────────────────
    moat_enabled: bool = True
    moat_version: str = "v41"

    # ── Agents ───────────────────────────────────────────────────
    agent_count: int = 250
    verifier_count: int = 15

    # ── RAG ──────────────────────────────────────────────────────
    rag_enabled: bool = True
    rag_embedding_model: str = "text-embedding-3-small"
    rag_embedding_dim: int = 1536
    rag_max_results: int = 10

    # ── Feature Flags ───────────────────────────────────────────
    enable_voice_input: bool = True
    enable_voice_output: bool = True
    enable_thinking_panel: bool = True

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: list[str] = ["*"]

    # ── Paths ────────────────────────────────────────────────────
    static_dir: str = "static"
    templates_dir: str = "templates"

    @property
    def database_url_resolved(self) -> str:
        """Return the first available database URL."""
        return self.database_url or self.neon_database_url or ""

    @property
    def redis_url_resolved(self) -> str:
        """Return the first available Redis URL."""
        return self.redis_url or self.upstash_redis_url or ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


# Create the singleton instance — THIS is what `from core.config import settings` imports
settings = Settings()

# Override with environment variables (in case BaseSettings didn't pick them up)
# This handles the case where pydantic-settings isn't installed
if not settings.database_url:
    settings.database_url = os.environ.get("DATABASE_URL", "")
if not settings.neon_database_url:
    settings.neon_database_url = os.environ.get("NEON_DATABASE_URL", "")
if not settings.redis_url:
    settings.redis_url = os.environ.get("REDIS_URL", "")
if not settings.upstash_redis_url:
    settings.upstash_redis_url = os.environ.get("UPSTASH_REDIS_URL", "")
if not settings.sarvam_api_key:
    settings.sarvam_api_key = os.environ.get("SARVAM_API_KEY", "")
if not settings.groq_api_key:
    settings.groq_api_key = os.environ.get("GROQ_API_KEY", "")
if not settings.openai_api_key:
    settings.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
if not settings.gemini_api_key:
    settings.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
if not settings.deepseek_api_key:
    settings.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
if not settings.openrouter_api_key:
    settings.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")

# JWT secret from env (override default if set)
_env_jwt = os.environ.get("JWT_SECRET", "")
if _env_jwt:
    settings.jwt_secret = _env_jwt

# Auth enforcement from env
_env_enforce = os.environ.get("ENFORCE_AUTH", "false").lower()
settings.enforce_auth = _env_enforce == "true"

# Rate limit from env
_env_rate = os.environ.get("RATE_LIMIT_PER_MIN", "")
if _env_rate:
    try:
        settings.rate_limit_per_min = int(_env_rate)
    except ValueError:
        pass


# ════════════════════════════════════════════════════════════════════════
# TIERED LLM ROUTING — the core latency fix
# ════════════════════════════════════════════════════════════════════════
LLM_ROUTING = {
    "simple": {
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "max_tokens": 512,
        "temperature": 0.3,
        "timeout": 10,
        "expected_latency_ms": 1000,
        "description": "Greetings, definitions, short questions (70% of queries)",
    },
    "medium": {
        "provider": "sarvam",
        "model": "sarvam-30b",
        "max_tokens": 1024,
        "temperature": 0.4,
        "timeout": 30,
        "expected_latency_ms": 8000,
        "description": "Standard legal questions requiring moderate analysis (20%)",
    },
    "complex": {
        "provider": "sarvam",
        "model": "sarvam-105b",
        "max_tokens": 2048,
        "temperature": 0.5,
        "timeout": 120,
        "expected_latency_ms": 60000,
        "description": "Case analysis, constitutional questions, multi-party disputes (10%)",
    },
}


def classify_complexity(query: str) -> str:
    """
    Classify query complexity to route to the right LLM.
    Returns: 'simple', 'medium', or 'complex'

    Heuristics:
      - Short queries (< 10 words) → simple
      - Greetings/definitions → simple
      - Case analysis, constitutional → complex
      - Everything else → medium
    """
    query_lower = query.lower().strip()
    word_count = len(query_lower.split())

    # SIMPLE: greetings, short questions, basic definitions
    simple_patterns = [
        "hello", "hi", "hey", "thanks", "thank you",
        "what is", "define", "explain briefly",
        "summarize", "list", "who is", "when did",
    ]
    if any(query_lower.startswith(p) for p in simple_patterns) or word_count < 10:
        return "simple"

    # COMPLEX: deep legal analysis
    complex_patterns = [
        "analyse", "analyze", "case analysis", "constitutional",
        "precedent", "multi-party", "appeal", "supreme court",
        "constitutional validity", "judicial review", "writ petition",
        "public interest litigation", "pil", "detailed analysis",
        "compare and contrast", "evaluate the legality",
    ]
    if any(p in query_lower for p in complex_patterns) or word_count > 100:
        return "complex"

    # MEDIUM: standard legal questions
    return "medium"


# ════════════════════════════════════════════════════════════════════════
# PUBLIC PATHS — exempt from JWT auth
# ════════════════════════════════════════════════════════════════════════
PUBLIC_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/api/status",
    "/auth/token",
}

PUBLIC_PREFIXES = (
    "/static/",
    "/docs/",
    "/redoc/",
)


# ════════════════════════════════════════════════════════════════════════
# LLM PROVIDER CONFIG (detailed, with base URLs)
# ════════════════════════════════════════════════════════════════════════
LLM_PROVIDERS = {
    "sarvam": {
        "api_key": settings.sarvam_api_key,
        "base_url": "https://api.sarvam.ai/v1",
        "models": ["sarvam-105b", "sarvam-30b"],
    },
    "groq": {
        "api_key": settings.groq_api_key,
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
    },
    "openai": {
        "api_key": settings.openai_api_key,
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini"],
    },
    "gemini": {
        "api_key": settings.gemini_api_key,
        "base_url": "https://generativelanguage.googleapis.com/v1",
        "models": ["gemini-2.0-flash", "gemini-pro"],
    },
    "deepseek": {
        "api_key": settings.deepseek_api_key,
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "openrouter": {
        "api_key": settings.openrouter_api_key,
        "base_url": "https://openrouter.ai/api/v1",
        "models": ["auto", "anthropic/claude-3.5-sonnet"],
    },
}


# ════════════════════════════════════════════════════════════════════════
# FEATURE FLAGS
# ════════════════════════════════════════════════════════════════════════
FEATURE_FLAGS = {
    "voice_input": settings.enable_voice_input,
    "voice_output": settings.enable_voice_output,
    "thinking_panel": settings.enable_thinking_panel,
    "streaming_chat": settings.enable_streaming,
    "redis_cache": bool(settings.redis_url_resolved),
    "rate_limiting": True,
    "jwt_auth": settings.enforce_auth,
    "moat_evolution": settings.moat_enabled,
    "agent_network": True,
    "ai_judge": True,
    "verifiers": True,
    "rag_engine": settings.rag_enabled,
}


# ════════════════════════════════════════════════════════════════════════
# BLOCKED SCANNER PATHS
# ════════════════════════════════════════════════════════════════════════
BLOCKED_SCANNER_PATHS = [
    "/.env",
    "/.env.local",
    "/.env.production",
    "/.streamlit/secrets.toml",
    "/file=../.env",
    "/file=../../.env",
    "/api/config",
    "/api/predict",
]


# Log config on import (helps with debugging)
logger.info(f"Config loaded: {settings.app_name} v{settings.version}")
logger.info(f"  Environment: {settings.environment}")
logger.info(f"  Database: {'configured' if settings.database_url_resolved else 'NOT SET'}")
logger.info(f"  Redis: {'configured' if settings.redis_url_resolved else 'not set (in-memory fallback)'}")
logger.info(f"  Auth: {'enforced' if settings.enforce_auth else 'disabled (open)'}")
logger.info(f"  Rate limit: {settings.rate_limit_per_min}/min per IP")
