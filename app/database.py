from beanie import init_beanie
from app.models import User, Task, Reminder, ConversationTurn
from app.config import settings
from app.utils.logger import setup_logger
from motor.motor_asyncio import AsyncIOMotorClient

logger = setup_logger(__name__)


async def init_db(client: AsyncIOMotorClient):
    """Initializes the database connection and sets up Beanie with the document models."""
    try:
        logger.info(f"Initializing database: {settings.MONGO_DB_NAME}")

        await init_beanie(
            database=client.get_database(settings.MONGO_DB_NAME),  # type: ignore
            document_models=[User, Task, Reminder, ConversationTurn],
        )
        logger.info("Database models registered successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
