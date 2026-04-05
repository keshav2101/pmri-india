"""
core/config.py — Pydantic settings for PMRI India backend.
"""
from __future__ import annotations
from functools import lru_cache
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DB — set DATABASE_URL in .env (supports Supabase postgresql:// URIs)
    database_url: str = "postgresql+asyncpg://pmri_india:pmri_india_secret@localhost:5432/pmri_india"

    @field_validator("database_url", mode="before")
    def assemble_db_connection(cls, v: str | None) -> str:
        if not v:
            return "postgresql+asyncpg://pmri_india:pmri_india_secret@localhost:5432/pmri_india"
        # Supabase returns postgresql:// — convert to asyncpg dialect
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        # Already correct dialect
        if v.startswith("postgresql+asyncpg://"):
            return v
        return v

    # JWT
    jwt_secret: str = "pmri_india_jwt_secret_change_in_prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    # Market data
    market_provider: str = "demo"
    market_api_key: str  = ""

    # App
    demo_mode: bool = True
    log_level: str  = "INFO"
    cors_origins: str = "http://localhost:3001"

    # Model
    model_artifacts_path: str = "/app/artifacts"
    ml_module_path: str       = "/app/ml"

    # Tier limits (INR) — base defaults, overridden by DB rules_config
    retail_max_notional:       float = 1_000_000
    inst_basic_max_notional:   float = 10_000_000
    inst_premium_max_notional: float = 50_000_000
    min_premium_inr:           float = 500.0
    intraday_cutoff_ist:       str   = "15:30"   # HH:MM

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
