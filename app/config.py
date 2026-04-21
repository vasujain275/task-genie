try:
    from pydantic import AliasChoices, Field
    from pydantic_settings import BaseSettings
except Exception:  # pragma: no cover - test fallback

    class BaseSettings:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def __init_subclass__(cls, **kwargs):
            return super().__init_subclass__(**kwargs)

    def Field(default=None, **_kwargs):
        return default


class Settings(BaseSettings):
    MONGO_URI: str = ""
    MONGO_DB_NAME: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    WEBHOOK_URL: str = ""  # Full webhook URL (e.g., https://yourdomain.com/webhook)
    TELEGRAM_WEBHOOK_SECRET_TOKEN: str = ""
    REDIS_URL: str = ""  # For aiogram FSM storage
    ENCRYPTION_KEY: str = ""
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    MODEL: str = Field(
        default="gpt-5-nano",
        validation_alias=AliasChoices("MODEL", "LITELLM_MODEL", "LLM"),
    )
    TRACING_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = ""
    LANGFUSE_PROJECT: str = ""

    @property
    def LLM(self) -> str:
        return self.MODEL

    @property
    def LITELLM_MODEL(self) -> str:
        return self.MODEL

    @property
    def tracing_enabled(self) -> bool:
        return bool(
            self.TRACING_ENABLED
            and self.LANGFUSE_PUBLIC_KEY
            and self.LANGFUSE_SECRET_KEY
            and self.LANGFUSE_HOST
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
