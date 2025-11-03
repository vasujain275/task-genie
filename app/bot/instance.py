"""
Bot instance creation
Separated so it can be imported without circular dependencies
"""

from aiogram import Bot
from app.config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
