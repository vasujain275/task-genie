"""
Dispatcher setup and handler registration
"""

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from app.config import settings
from app.bot.handlers import start, settings as settings_handler
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def setup_dispatcher() -> Dispatcher:
    """
    Creates and configures the dispatcher
    Registers all handlers
    """
    try:
        logger.info("Setting up dispatcher with Redis storage")
        storage = RedisStorage.from_url(
            settings.REDIS_URL,
            # state_ttl=3600,  # state expires in 1 hour
            # data_ttl=3600,  # associated data expires in 1 hour
        )

        dp = Dispatcher(storage=storage)

        # Registering Routers
        dp.include_router(start.router)
        dp.include_router(settings_handler.router)

        logger.info("Dispatcher setup complete with all routers registered")
        return dp

    except Exception as e:
        logger.error(f"Failed to setup dispatcher: {e}", exc_info=True)
        raise
