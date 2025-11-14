from beanie import Document
from typing import Optional
from datetime import datetime
from pydantic import Field
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class User(Document):
    telegram_id: int  # Keep as telegram_id for clarity
    name: str
    username: Optional[str] = None  # Telegram username
    openai_key: Optional[str] = None
    timezone: str = "UTC"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        use_state_management = True
        indexes = [
            "telegram_id",  # Index for fast lookups
        ]

    @classmethod
    async def get_or_create(
        cls, telegram_id: int, name: str, username: Optional[str] = None
    ):
        """Get user by telegram_id or create if not exists - convenient for aiogram handlers"""
        try:
            user = await cls.find_one(cls.telegram_id == telegram_id)
            if not user:
                logger.info(f"Creating new user: {telegram_id}")
                user = cls(telegram_id=telegram_id, name=name, username=username)
                await user.insert()
                logger.info(f"User created successfully: {telegram_id}")
            else:
                logger.debug(f"User found: {telegram_id}")
            return user
        except Exception as e:
            logger.error(
                f"Error in get_or_create for user {telegram_id}: {e}", exc_info=True
            )
            raise

    @classmethod
    async def get_by_telegram_id(cls, telegram_id: int):
        """Get user by telegram_id - convenient for aiogram handlers"""
        try:
            logger.debug(f"Fetching user by telegram_id: {telegram_id}")
            return await cls.find_one(cls.telegram_id == telegram_id)
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {e}", exc_info=True)
            raise
