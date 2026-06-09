"""Application configuration using Pydantic Settings."""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "PlagX"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database - Must be PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://plagx:plagx_secret@localhost:5432/plagx"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-this-in-production-to-a-real-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "./uploads"
    REPORTS_DIR: str = "./reports"
    VECTOR_DB_DIR: str = "./vector_db"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # AI Model
    SENTENCE_TRANSFORMER_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Engine Settings
    CHUNK_SIZE_WORDS: int = 75
    CHUNK_OVERLAP_PERCENT: float = 0.20
    MIN_EXACT_MATCH_WORDS: int = 8
    NGRAM_SIZE: int = 5
    SEMANTIC_HIGH_THRESHOLD: float = 0.88
    SEMANTIC_MED_THRESHOLD: float = 0.80
    SEMANTIC_LOW_THRESHOLD: float = 0.70

    # Scoring Weights
    EXACT_MATCH_WEIGHT: float = 0.40
    SEMANTIC_MATCH_WEIGHT: float = 0.40
    SOURCE_DENSITY_WEIGHT: float = 0.20

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def reports_path(self) -> Path:
        p = Path(self.REPORTS_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def vector_db_path(self) -> Path:
        p = Path(self.VECTOR_DB_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        
    def validate_environment(self):
        """Fail fast if environment is misconfigured."""
        if not self.DATABASE_URL.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string.")
        if not self.REDIS_URL.startswith("redis"):
            raise ValueError("REDIS_URL must be configured.")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
