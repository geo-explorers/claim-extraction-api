"""Configuration settings for the Claim API.

Loads configuration from environment variables using Pydantic Settings.
All settings can be overridden via .env file or environment variables.

Usage:
    from src.config.settings import Settings

    settings = Settings()  # Instantiated via FastAPI lifespan, not at module level
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    gemini_api_key: str = Field(description="Google Gemini API key (required)")
    gemini_model: str = Field(
        default="gemini-2.5-flash", description="Gemini model name"
    )
    gemini_temperature: float = Field(
        default=0.2, description="Generation temperature"
    )
    port: int = Field(default=8000, description="API server port (Railway sets via PORT)")
    log_level: str = Field(default="INFO", description="Logging level")
