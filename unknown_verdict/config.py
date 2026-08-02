"""
Configuration for Unknown Verdict v41.0
Centralized settings using pydantic-settings.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "Unknown Verdict"
    APP_VERSION: str = "41.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # Sarvam AI
    SARVAM_API_KEY: str = Field(default="", description="Sarvam AI API key")
    SARVAM_105B_MODEL: str = "sarvam-105b"
    SARVAM_30B_MODEL: str = "sarvam-30b"
    SARVAM_BASE_URL: str = "https://api.sarvam.ai/v1"
    SARVAM_TIMEOUT: int = 120
    SARVAM_MAX_RETRIES: int = 3

    # Database & Vector Store (Neon Postgres with pgvector)
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/unknown_verdict"
    PGVECTOR_ENABLED: bool = True
    VECTOR_DIMENSIONS: int = 384

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Razorpay
    RAZORPAY_KEY_ID: str = "rzp_test_XXXXXXXX"
    RAZORPAY_KEY_SECRET: str = ""
    PAYMENT_AMOUNT: int = 200  # ₹2 in paise

    # Stripe
    STRIPE_API_KEY: str = ""

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 7860

    # Security
    JWT_SECRET: str = "unknown-verdict-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: List[str] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"

    # Agents
    AGENT_COUNT: int = 250
    VERIFIER_COUNT: int = 15

    # RAG
    RAG_CHUNK_SIZE: int = 1024
    RAG_CHUNK_OVERLAP: int = 128
    RAG_TOP_K: int = 5

    # Compliance
    COMPLIANCE_MIN_SCORE: float = 0.75

    # California DROP
    DROP_API_URL: str = "https://oag.ca.gov/privacy/data-brokers"
    DROP_ENABLED: bool = True

    # Infinity mode
    INFINITY_MODE: bool = True

    # Moat v41.0 — Self-Evolving Intelligence
    MOAT_VERSION: str = "41.0"
    MOAT_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    MOAT_EMBEDDING_DIM: int = 384
    MOAT_GAP_THRESHOLD: float = 0.40
    MOAT_MIN_CONFIDENCE_TO_PROMOTE: float = 0.72
    MOAT_MESH_SYNC_INTERVAL_SEC: int = 300
    MOAT_JUDGE_MIN_CASES_BEFORE_EVOLUTION: int = 25

    # Content site
    CONTENT_SITE_URL: str = "https://www.advocacayalawfrim.in"

    @property
    def is_sarvam_configured(self) -> bool:
        return bool(self.SARVAM_API_KEY) and self.SARVAM_API_KEY != "your_sarvam_api_key_here"

    @property
    def is_razorpay_configured(self) -> bool:
        return "test" in self.RAZORPAY_KEY_ID or "live" in self.RAZORPAY_KEY_ID

    @property
    def is_database_configured(self) -> bool:
        return bool(self.DATABASE_URL) and "localhost" not in self.DATABASE_URL and "user:password" not in self.DATABASE_URL

    @property
    def is_stripe_configured(self) -> bool:
        return bool(self.STRIPE_API_KEY) and self.STRIPE_API_KEY != ""


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
