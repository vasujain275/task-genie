from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = ""
    MONGO_DB_NAME: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    WEBHOOK_URL: str = ""  # Full webhook URL (e.g., https://yourdomain.com/webhook)
    REDIS_URL: str = ""  # For aiogram FSM storage
    ENCRYPTION_KEY: str = ""
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    class Config:
        env_file = ".env"


settings = Settings()
