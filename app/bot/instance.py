"""
Bot instance creation
Separated so it can be imported without circular dependencies
"""

from aiogram import Bot
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

logger.info("Initializing Telegram Bot instance")
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
