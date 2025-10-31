"""
Utility functions to simplify aiogram FSM integration with Beanie models.
"""

from typing import Optional
from aiogram.types import Message, User as TelegramUser
from app.models import User, Task, Reminder
from datetime import datetime


async def ensure_user(telegram_user: TelegramUser) -> User:
    """
    Ensure user exists in database, create if not.
    Use this at the start of any handler to guarantee user exists.

    Example:
        @router.message(Command("start"))
        async def start_handler(message: Message):
            user = await ensure_user(message.from_user)
            await message.answer(f"Welcome {user.name}!")
    """
    return await User.get_or_create(
        telegram_id=telegram_user.id,
        name=telegram_user.full_name,
        username=telegram_user.username
    )
