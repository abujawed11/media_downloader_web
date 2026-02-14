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


# Create a global settings instance
settings = Settings()
