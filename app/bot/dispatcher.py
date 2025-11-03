"""
Dispatcher setup and handler registration
"""

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from app.config import settings
from app.bot.handlers import start


def setup_dispatcher() -> Dispatcher:
    """
    Creates and configures the dispatcher
    Registers all handlers
    """

    storage = RedisStorage.from_url(
        settings.REDIS_URL,
        # state_ttl=3600,  # state expires in 1 hour
        # data_ttl=3600,  # associated data expires in 1 hour
    )

    dp = Dispatcher(storage=storage)

    dp.include_router(start.router)

    return dp
