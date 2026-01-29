"""
Centralized Configuration for BrawlGPT.
Uses Pydantic Settings for validation and environment variable loading.
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application settings with validation.
    All settings can be overridden via environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # API Keys (Required)
    # =========================================================================
    brawl_api_key: str = Field(
        ...,
        description="Brawl Stars API key from developer portal"
    )
    openrouter_api_key: str = Field(
        ...,
        description="OpenRouter API key for LLM access"
    )
    secret_key: str = Field(
        default="change-me-in-production-min-32-chars",
        min_length=32,
        description="Secret key for JWT token signing"
    )

    # =========================================================================
    # Database
    # =========================================================================
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/brawlgpt_db",
        description="PostgreSQL connection string (async)"
    )

    # =========================================================================
    # Redis
    # =========================================================================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    redis_enabled: bool = Field(
        default=True,
        description="Enable Redis caching (falls back to in-memory if disabled)"
    )

    # =========================================================================
    # CORS
    # =========================================================================
    allowed_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins"
    )

    @property
    def cors_origins(self) -> list[str]:
        """Parse allowed origins into a list."""
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    # =========================================================================
    # Rate Limiting
    # =========================================================================
    rate_limit_player: str = Field(
        default="30/minute",
        description="Rate limit for player endpoints"
    )
    rate_limit_chat: str = Field(
        default="10/minute",
        description="Rate limit for chat endpoints"
    )
    rate_limit_cache: str = Field(
        default="10/minute",
        description="Rate limit for cache management endpoints"
    )

    # =========================================================================
    # Logging
    # =========================================================================
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_format: str = Field(
        default="json",
        description="Log format: 'json' for structured, 'text' for human-readable"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v

    # =========================================================================
    # AI Agent
    # =========================================================================
    ai_model: str = Field(
        default="anthropic/claude-sonnet-4.5",
        description="OpenRouter model ID for AI agent"
    )
    ai_max_tokens: int = Field(
        default=2000,
        ge=100,
        le=100000,
        description="Maximum tokens for AI responses"
    )
    ai_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="AI temperature for response generation"
    )

    # =========================================================================
    # Feature Flags
    # =========================================================================
    enable_meta_crawler: bool = Field(
        default=True,
        description="Enable the meta crawler service"
    )
    enable_progression_tracking: bool = Field(
        default=True,
        description="Enable player progression tracking"
    )
    enable_agent_tools: bool = Field(
        default=True,
        description="Enable AI agent tools (function calling)"
    )
    enable_global_meta_aggregation: bool = Field(
        default=True,
        description="Enable global meta aggregation service"
    )
    enable_synergy_analysis: bool = Field(
        default=True,
        description="Enable brawler synergy analysis"
    )
    enable_trend_detection: bool = Field(
        default=True,
        description="Enable meta trend detection"
    )

    # =========================================================================
    # Meta Crawler
    # =========================================================================
    meta_collection_interval_hours: int = Field(
        default=6,
        ge=1,
        le=24,
        description="Hours between meta collection runs"
    )
    meta_max_players_per_range: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Maximum players to analyze per trophy range"
    )
    
    # =========================================================================
    # Global Meta Intelligence
    # =========================================================================
    global_meta_interval_minutes: int = Field(
        default=60,
        ge=15,
        le=360,
        description="Minutes between global meta aggregation runs"
    )
    synergy_analysis_interval_hours: int = Field(
        default=2,
        ge=1,
        le=12,
        description="Hours between synergy analysis runs"
    )
    trend_detection_interval_hours: int = Field(
        default=6,
        ge=1,
        le=24,
        description="Hours between trend detection runs"
    )
    ai_min_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for AI insights"
    )
    meta_history_retention_days: int = Field(
        default=30,
        ge=7,
        le=365,
        description="Days to retain meta history data"
    )
    trend_history_retention_days: int = Field(
        default=90,
        ge=14,
        le=365,
        description="Days to retain trend history data"
    )

    # =========================================================================
    # Cache TTLs (seconds)
    # =========================================================================
    cache_ttl_player: int = Field(
        default=300,
        ge=60,
        description="Player data cache TTL (seconds)"
    )
    cache_ttl_battlelog: int = Field(
        default=300,
        ge=60,
        description="Battle log cache TTL (seconds)"
    )
    cache_ttl_insights: int = Field(
        default=900,
        ge=300,
        description="AI insights cache TTL (seconds)"
    )
    cache_ttl_meta: int = Field(
        default=21600,
        ge=3600,
        description="Meta snapshot cache TTL (seconds)"
    )
    cache_ttl_brawlers: int = Field(
        default=86400,
        ge=3600,
        description="Static brawler data cache TTL (seconds)"
    )
    cache_ttl_events: int = Field(
        default=3600,
        ge=600,
        description="Event rotation cache TTL (seconds)"
    )

    # =========================================================================
    # Application
    # =========================================================================
    app_name: str = Field(
        default="BrawlGPT",
        description="Application name"
    )
    app_version: str = Field(
        default="2.0.0",
        description="Application version"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded once.
    """
    return Settings()


# Convenience function for quick access
def settings() -> Settings:
    """Get settings instance."""
    return get_settings()
