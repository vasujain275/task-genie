from beanie import Document
from typing import Optional
from datetime import datetime
from pydantic import Field

class User(Document):
    telegram_id: int  # Keep as telegram_id for clarity
    name: str
    username: Optional[str] = None  # Telegram username
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None
    default_ai: str = "gemini"
    timezone: str = "Asia/Kolkata"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        use_state_management = True
        indexes = [
            "telegram_id",  # Index for fast lookups
        ]

    @classmethod
    async def get_or_create(cls, telegram_id: int, name: str, username: Optional[str] = None):
        """Get user by telegram_id or create if not exists - convenient for aiogram handlers"""
        user = await cls.find_one(cls.telegram_id == telegram_id)
        if not user:
            user = cls(telegram_id=telegram_id, name=name, username=username)
            await user.insert()
        return user

    @classmethod
    async def get_by_telegram_id(cls, telegram_id: int):
        """Get user by telegram_id - convenient for aiogram handlers"""
        return await cls.find_one(cls.telegram_id == telegram_id)
