"""
config.py — Centralized environment variable loading and validation.
All settings are loaded from environment variables only. No hardcoded secrets.
"""

import os
import json
import logging
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, validator

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")

    # Gemini AI
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")

    # Brevo Email
    brevo_api_key: str = Field(..., env="BREVO_API_KEY")
    email_sender: str = Field(..., env="EMAIL_SENDER")
    email_sender_name: str = Field(..., env="EMAIL_SENDER_NAME")
    gmail_app_password: str = Field(..., env="GMAIL_APP_PASSWORD")
    
    # Google Sheets
    google_creds_json: str = Field(..., env="GOOGLE_CREDS_JSON")
    google_sheet_name: str = Field(..., env="GOOGLE_SHEET_NAME")

    # App
    base_url: str = Field(..., env="BASE_URL")
    port: int = Field(default=8000, env="PORT")

    # Optional tuning
    rate_limit_delay: float = Field(default=2.0, env="RATE_LIMIT_DELAY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def google_creds_dict(self) -> dict:
        """Parse the JSON credentials string into a dict."""
        try:
            return json.loads(self.google_creds_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GOOGLE_CREDS_JSON: {e}")
            raise ValueError("GOOGLE_CREDS_JSON is not valid JSON") from e

    @property
    def webhook_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/webhook"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — loaded once at startup."""
    return Settings()
