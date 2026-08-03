"""
core/config.py
==============
Central configuration for Unknown Verdict v41.0.

All 25 HF Space secrets are read from the environment via pydantic-settings.
Missing non-critical secrets degrade gracefully instead of crashing on import.

Secrets wired:
  DATABASE_URL, REDIS_URL, ENABLE_WEB_SEARCH, ENABLE_TARGETED_SEARCH,
  TARGETED_SEARCH_DOMAINS, ADMIN_SECRET, USE_VERDICT_ENGINE, VERDICT_ENGINE_MODE,
  OPENAI_API_KEY, LLAMA_CLOUD_API_KEY, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,
  GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY, ADMIN_KEY,
  JWR_SECRET, JWT_SECRET, SERPAPI_KEY, LINKEDIN_ACCESS_TOKEN,
  LINKEDIN_USER_ID, DEEPSEEK_API_KEY, GITHUB_TOKEN, SARVAM_API_KEY
"""

from __future__ import annotations

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
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Core infrastructure ──
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/unknown_verdict"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Feature toggles ──
    ENABLE_WEB_SEARCH: bool = False
    ENABLE_TARGETED_SEARCH: bool = False
    TARGETED_SEARCH_DOMAINS: List[str] = Field(default_factory=list)

    # ── Verdict engine ──
    USE_VERDICT_ENGINE: bool = False
    VERDICT_ENGINE_MODE: str = "balanced"  # strict | balanced | lenient

    # ── Admin / JWT ──
    ADMIN_SECRET: str = ""
    ADMIN_KEY: str = ""
    JWT_SECRET: str = "change-me-in-production"
    JWR_SECRET: str = ""

    # ── LLM API keys (6 providers) ──
    SARVAM_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # ── Search / parsing ──
    SERPAPI_KEY: str = ""
    LLAMA_CLOUD_API_KEY: str = ""

    # ── Payments ──
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # ── Integrations ──
    GITHUB_TOKEN: str = ""
    LINKEDIN_ACCESS_TOKEN: str = ""
    LINKEDIN_USER_ID: str = ""

    # ── Runtime tuning ──
    APP_NAME: str = "Unknown Verdict"
    APP_VERSION: str = "41.0"
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"

    # LLM defaults — tuned to kill the 100s latency
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_TOKENS_DEFAULT: int = 1024
    LLM_MAX_TOKENS_CHAT: int = 512
    LLM_MAX_TOKENS_COMPLEX: int = 2048
    LLM_TEMPERATURE: float = 0.3
    LLM_STREAM_ENABLED: bool = True

    # Cache
    CACHE_TTL_SECONDS: int = 3600
    CACHE_PREFIX: str = "uv:cache:"

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── Validators ──
    @field_validator("ENABLE_WEB_SEARCH", "ENABLE_TARGETED_SEARCH",
                     "USE_VERDICT_ENGINE", mode="before")
    @classmethod
    def _coerce_bool(cls, v):
        return _as_bool(v)

    @field_validator("TARGETED_SEARCH_DOMAINS", mode="before")
    @classmethod
    def _coerce_list(cls, v):
        return _as_list(v)

    # ── Convenience properties ──
    @property
    def available_llm_providers(self) -> List[str]:
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
        return [k for k in (self.ADMIN_KEY, self.ADMIN_SECRET) if k]

    @property
    def jwt_signing_key(self) -> str:
        return self.JWT_SECRET or self.JWR_SECRET or "change-me-in-production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
