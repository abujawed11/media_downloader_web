"""Application configuration loaded from environment variables."""
from dotenv import load_dotenv
import os
from typing import List

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings."""

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # CORS Origins
    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"
        ).split(",")
    ]

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").upper()

    # yt-dlp Configuration
    YTDLP_OUTPUT_PATH: str = os.getenv("YTDLP_OUTPUT_PATH", "./downloads")
    YTDLP_FORMAT: str = os.getenv("YTDLP_FORMAT", "best")

    # Cookie files path
    COOKIES_PATH: str = os.getenv("COOKIES_PATH", "./cookies")

    # Redis & Celery Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    CELERY_WORKER_CONCURRENCY: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/medialib"
    )

    # Storage Configuration
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")  # "local" or "s3"
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./media_storage")

    # S3-compatible storage (Cloudflare R2 / AWS S3)
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "")
    S3_ACCESS_KEY_ID: str = os.getenv("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY: str = os.getenv("S3_SECRET_ACCESS_KEY", "")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "medialib")
    S3_REGION: str = os.getenv("S3_REGION", "auto")
    CDN_URL: str = os.getenv("CDN_URL", "")


# Create a global settings instance
settings = Settings()
