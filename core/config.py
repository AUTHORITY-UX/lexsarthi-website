"""
core/config.py
==============
Central configuration for Unknown Verdict v41.0.
"""
from __future__ import annotations

import json
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
    # Store as string to avoid JSON parsing issues
    TARGETED_SEARCH_DOMAINS_RAW: str = ""

    # ── Verdict engine ──
    USE_VERDICT_ENGINE: bool = False
    VERDICT_ENGINE_MODE: str = "balanced"

    # ── Admin / JWT ──
    ADMIN_SECRET: str = ""
    ADMIN_KEY: str = ""
    JWT_SECRET: str = ""
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

    # LLM defaults
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
        """JWT signing key - uses ADMIN_SECRET as fallback"""
        if self.ADMIN_SECRET:
            return self.ADMIN_SECRET
        if self.JWT_SECRET:
            return self.JWT_SECRET
        if self.JWR_SECRET:
            return self.JWR_SECRET
        return "change-me-in-production"

    @property
    def TARGETED_SEARCH_DOMAINS(self) -> List[str]:
        """Parse TARGETED_SEARCH_DOMAINS_RAW safely - handles comma-separated, JSON, or single values"""
        raw = self.TARGETED_SEARCH_DOMAINS_RAW
        if not raw:
            # Default domains if nothing is set
            return [
                "https://www.indiacode.nic.in",
                "https://www.sci.gov.in",
                "https://legalaffairs.gov.in"
            ]
        
        # Try JSON parse first
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
            if isinstance(parsed, str):
                return [parsed.strip()]
        except json.JSONDecodeError:
            pass
        
        # Try comma-separated (your format)
        if "," in raw:
            domains = [x.strip() for x in raw.split(",") if x.strip()]
            if domains:
                return domains
        
        # Single value
        if raw.strip():
            return [raw.strip()]
        
        # Fallback
        return [
            "https://www.indiacode.nic.in",
            "https://www.sci.gov.in",
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        import logging
        logging.warning(f"Settings loading failed: {e}. Using fallback.")
        return Settings(
            DATABASE_URL=os.getenv("DATABASE_URL", "postgresql://localhost:5432/unknown_verdict"),
            REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379"),
            ADMIN_SECRET=os.getenv("ADMIN_SECRET", "fallback-secret"),
            TARGETED_SEARCH_DOMAINS_RAW=os.getenv("TARGETED_SEARCH_DOMAINS", ""),
        )


settings = get_settings()