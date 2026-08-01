"""
Configuration for Unknown Verdict v40.0 (Phase 2 - Production)
Centralized settings with DB, Redis, JWT, rate limiting, Prometheus.
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

    # Database (PostgreSQL + pgvector)
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/unknown_verdict"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_ECHO: bool = False
    PGVECTOR_ENABLED: bool = True
    VECTOR_DIMENSIONS: int = 1536

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5 minutes default
    REDIS_SESSION_TTL: int = 3600  # 1 hour
    REDIS_RATE_LIMIT_TTL: int = 60

    # JWT Authentication
    JWT_SECRET: str = "unknown-verdict-secret-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    API_KEY_HEADER: str = "X-API-Key"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_CHAT: str = "30/minute"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    LOG_FILE: str = "logs/unknown_verdict.log"
    LOG_ROTATION: str = "50 MB"
    LOG_RETENTION: str = "30 days"

    # Prometheus Metrics
    METRICS_ENABLED: bool = True
    METRICS_PATH: str = "/metrics"

    # External APIs
    INDIAN_KANOON_URL: str = "https://api.indiankanoon.org"
    INDIAN_KANOON_API_KEY: str = ""
    YAHOO_FINANCE_URL: str = "https://query1.finance.yahoo.com"
    NEWS_RSS_FEEDS: str = "https://www.livelaw.in/feed,https://www.barandbench.com/feed"

    # Razorpay
    RAZORPAY_KEY_ID: str = "rzp_test_XXXXXXXX"
    RAZORPAY_KEY_SECRET: str = ""
    PAYMENT_AMOUNT: int = 200  # ₹2 in paise

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 7860
    WORKERS: int = 1

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

    # Compression
    GZIP_MIN_SIZE: int = 1000

    # Health check
    HEALTH_CHECK_INTERVAL: int = 30  # seconds

    @property
    def is_sarvam_configured(self) -> bool:
        return bool(self.SARVAM_API_KEY) and self.SARVAM_API_KEY != "your_sarvam_api_key_here"

    @property
    def is_razorpay_configured(self) -> bool:
        return "test" in self.RAZORPAY_KEY_ID or "live" in self.RAZORPAY_KEY_ID

    @property
    def is_database_configured(self) -> bool:
        return "user:password" not in self.DATABASE_URL

    @property
    def is_redis_configured(self) -> bool:
        return "localhost" not in self.REDIS_URL or os.environ.get("REDIS_URL") is not None

    @property
    def rss_feeds(self) -> List[str]:
        return [f.strip() for f in self.NEWS_RSS_FEEDS.split(",") if f.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
