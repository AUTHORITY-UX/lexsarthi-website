"""
Configuration for Unknown Verdict v40.0
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
    APP_VERSION: str = "40.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # Sarvam AI
    SARVAM_API_KEY: str = Field(default="", description="Sarvam AI API key")
    SARVAM_105B_MODEL: str = "sarvam-105b"
    SARVAM_30B_MODEL: str = "sarvam-30b"
    SARVAM_BASE_URL: str = "https://api.sarvam.ai/v1"
    SARVAM_TIMEOUT: int = 120
    SARVAM_MAX_RETRIES: int = 3

    # Database & Vector Store
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/unknown_verdict"
    PGVECTOR_ENABLED: bool = True
    VECTOR_DIMENSIONS: int = 1536

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Razorpay
    RAZORPAY_KEY_ID: str = "rzp_test_XXXXXXXX"
    RAZORPAY_KEY_SECRET: str = ""
    PAYMENT_AMOUNT: int = 200  # ₹2 in paise

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

    @property
    def is_sarvam_configured(self) -> bool:
        return bool(self.SARVAM_API_KEY) and self.SARVAM_API_KEY != "your_sarvam_api_key_here"

    @property
    def is_razorpay_configured(self) -> bool:
        return "test" in self.RAZORPAY_KEY_ID or "live" in self.RAZORPAY_KEY_ID


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
