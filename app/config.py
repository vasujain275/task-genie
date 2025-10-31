from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI : str = ""
    MONGO_DB_NAME: str = ""
    TELEGRAM_BOT_TOEKN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""
    REDIS_URL: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
