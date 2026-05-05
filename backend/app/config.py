"""
config.py
─────────
All configuration comes from environment variables.
Pydantic-settings reads them automatically.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    environment: str = "development"
    app_name: str = "Incident Management System"

    # PostgreSQL (source of truth for Work Items + RCA)
    database_url: str = "postgresql+asyncpg://ims:ims_secret@localhost:5432/ims"

    # MongoDB (raw signal audit log / data lake)
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "ims"
    mongo_signals_collection: str = "raw_signals"

    # Redis (hot-path dashboard cache)
    redis_url: str = "redis://localhost:6379"
    redis_ttl_seconds: int = 30          # cache TTL for dashboard state

    # Ingestion tuning
    rate_limit_per_sec: int = 1000       # max signals per second
    buffer_size: int = 100_000           # ring buffer capacity
    debounce_window_seconds: int = 10    # dedup window
    debounce_threshold: int = 100        # signals before creating 1 work item


# Singleton – import this everywhere
settings = Settings()
