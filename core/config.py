"""
unknown_verdict.core.config
============================
Central configuration for Unknown Verdict v41.0.

Every secret is read from the environment (HF Spaces injects them automatically
as long as the variable name matches the Space secret name). We use
pydantic-settings so missing non-critical secrets degrade gracefully instead of
crashing the whole app on import.

All 25 HF Space secrets are wired here:

  DATABASE_URL            Neon PostgreSQL (with pgvector)
  REDIS_URL               Redis cache + rate-limit store
  ENABLE_WEB_SEARCH       "true"/"false" — toggle SerpAPI web search
  ENABLE_TARGETED_SEARCH  "true"/"false" — toggle domain-restricted search
  TARGETED_SEARCH_DOMAINS Comma-separated domain whitelist
  ADMIN_SECRET            Admin backdoor token (legacy)
  Token                   HF Spaces reserved (ignore)
  USE_VERDICT_ENGINE      "true"/"false" — toggle the verdict engine
  VERDICT_ENGINE_MODE     "strict" | "balanced" | "lenient"

  OPENAI_API_KEY          OpenAI (GPT-4o family)
  LLAMA_CLOUD_API_KEY     LlamaCloud / LlamaParse (doc parsing)
  RAZORPAY_KEY_ID         Razorpay payments
  RAZORPAY_KEY_SECRET     Razorpay payments
  GROQ_API_KEY            Groq (Llama 3 family, ultra-low latency)
  GEMINI_API_KEY          Google Gemini (1.5/2.0)
  OPENROUTER_API_KEY      OpenRouter (Mistral, Qwen, etc.)
  ADMIN_KEY               Admin API key (new)
  JWR_SECRET              (Legacy JWT secret alias)
  JWT_SECRET              JWT signing secret
  SERPAPI_KEY             SerpAPI for web search
  LINKEDIN_ACCESS_TOKEN   LinkedIn integration
  LINKEDIN_USER_ID        LinkedIn user
  DEEPSEEK_API_KEY        DeepSeek (reasoning)
  GITHUB_TOKEN            GitHub API (repo ops)
  SARVAM_API_KEY          Sarvam 105B/30B (primary legal LLM)
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _as_bool(v: object) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def _as_list(v: object) -> List[str]:
    if not v:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v).split(",") if x.strip()]


class Settings(BaseSettings):
    """Strongly-typed settings loaded from environment / HF Space secrets."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Core infrastructure ────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql://user:pass@localhost:5432/unknown_verdict",
        description="Neon PostgreSQL connection string (pgvector enabled).",
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching + rate limiting.",
    )

    # ── Feature toggles ───────────────────────────────────────────────────
    ENABLE_WEB_SEARCH: bool = False
    ENABLE_TARGETED_SEARCH: bool = False
    TARGETED_SEARCH_DOMAINS: List[str] = Field(default_factory=list)

    # ── Verdict engine ────────────────────────────────────────────────────
    USE_VERDICT_ENGINE: bool = False
    VERDICT_ENGINE_MODE: str = "balanced"  # strict | balanced | lenient

    # ── Admin / JWT ───────────────────────────────────────────────────────
    ADMIN_SECRET: str = ""
    ADMIN_KEY: str = ""
    JWT_SECRET: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    JWR_SECRET: str = ""

    # ── LLM API keys ──────────────────────────────────────────────────────
    SARVAM_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # ── Search / parsing ──────────────────────────────────────────────────
    SERPAPI_KEY: str = ""
    LLAMA_CLOUD_API_KEY: str = ""

    # ── Payments ──────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # ── Integrations ──────────────────────────────────────────────────────
    GITHUB_TOKEN: str = ""
    LINKEDIN_ACCESS_TOKEN: str = ""
    LINKEDIN_USER_ID: str = ""

    # ── Runtime tuning (not secrets, but env-tunable) ─────────────────────
    APP_NAME: str = "Unknown Verdict"
    APP_VERSION: str = "41.0"
    ENVIRONMENT: str = "production"  # production | staging | development
    LOG_LEVEL: str = "INFO"

    # LLM defaults — tuned to kill the 100-second latency
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_TOKENS_DEFAULT: int = 1024
    LLM_MAX_TOKENS_CHAT: int = 512
    LLM_MAX_TOKENS_COMPLEX: int = 2048
    LLM_TEMPERATURE: float = 0.3

    # Streaming
    LLM_STREAM_ENABLED: bool = True

    # Cache
    CACHE_TTL_SECONDS: int = 3600
    CACHE_PREFIX: str = "uv:cache:"

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── Validators ────────────────────────────────────────────────────────
    @field_validator("ENABLE_WEB_SEARCH", "ENABLE_TARGETED_SEARCH",
                     "USE_VERDICT_ENGINE", mode="before")
    @classmethod
    def _coerce_bool(cls, v):
        return _as_bool(v)

    @field_validator("TARGETED_SEARCH_DOMAINS", mode="before")
    @classmethod
    def _coerce_list(cls, v):
        return _as_list(v)

    # ── Convenience properties ───────────────────────────────────────────
    @property
    def available_llm_providers(self) -> List[str]:
        """Return provider names that have an API key configured."""
        mapping = [
            ("sarvam", self.SARVAM_API_KEY),
            ("openai", self.OPENAI_API_KEY),
            ("gemini", self.GEMINI_API_KEY),
            ("groq", self.GROQ_API_KEY),
            ("deepseek", self.DEEPSEEK_API_KEY),
            ("openrouter", self.OPENROUTER_API_KEY),
        ]
        return [name for name, key in mapping if key]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def admin_keys(self) -> List[str]:
        """All valid admin tokens (both legacy and new)."""
        return [k for k in (self.ADMIN_KEY, self.ADMIN_SECRET) if k]

    @property
    def jwt_signing_key(self) -> str:
        """Prefer JWT_SECRET, fall back to JWR_SECRET for backward compat."""
        return self.JWT_SECRET or self.JWR_SECRET or "change-me-in-production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton — call this everywhere, never instantiate directly."""
    return Settings()


# Eager singleton for convenience imports
settings = get_settings()
