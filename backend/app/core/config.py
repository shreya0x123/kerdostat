import os

def load_env_manual():
    # Look for .env in the workspace root and backend root
    paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
    ]
    for path in paths:
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            os.environ[key.strip()] = val.strip().strip("'\"")
        except Exception:
            pass

load_env_manual()

class Settings:
    APP_NAME: str = "Kerdostat"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        self.ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
        self.ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
        self.ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    def is_alpaca_configured(self) -> bool:
        return bool(self.ALPACA_API_KEY and self.ALPACA_SECRET_KEY)

settings = Settings()
