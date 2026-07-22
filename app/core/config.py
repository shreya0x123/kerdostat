"""
kerdostat/app/core/config.py
Centralised settings loaded from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "Kerdostat"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Alpaca
    ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "")
    ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
    ALPACA_BASE_URL: str = os.getenv(
        "ALPACA_BASE_URL", "https://paper-api.alpaca.markets"
    )

    def is_alpaca_configured(self) -> bool:
        return bool(self.ALPACA_API_KEY and self.ALPACA_SECRET_KEY)


settings = Settings()
