"""
MongoDB-based checkpointing for LangGraph with daily conversation isolation
"""

from datetime import datetime, date
from typing import Optional
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from pymongo import AsyncMongoClient
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_conversation_id(user_id: int, conversation_date: Optional[date] = None) -> str:
    """
    Generate a unique conversation ID based on user ID and date.
    This ensures each day has a fresh conversation context.

    Args:
        user_id: Telegram user ID
        conversation_date: Date for the conversation (defaults to today)

    Returns:
        Conversation ID in format "user_{user_id}_date_{YYYY-MM-DD}"
    """
    if conversation_date is None:
        conversation_date = datetime.utcnow().date()

    return f"user_{user_id}_date_{conversation_date.isoformat()}"


# Global instances
_mongo_client: Optional[AsyncMongoClient] = None  # type: ignore[valid-type]
_checkpointer: Optional[AsyncMongoDBSaver] = None


async def get_checkpointer() -> AsyncMongoDBSaver:
    """
    Get or create the global MongoDB checkpointer instance.

    Returns:
        AsyncMongoDBSaver instance for LangGraph checkpointing
    """
    global _mongo_client, _checkpointer

    if _checkpointer is None:
        # Create MongoDB client and checkpointer
        _mongo_client = AsyncMongoClient(settings.MONGO_URI)  # type: ignore[call-arg]
        _checkpointer = AsyncMongoDBSaver(
            client=_mongo_client,
            db_name=settings.MONGO_DB_NAME,
            checkpoint_collection_name="langgraph_checkpoints",
            writes_collection_name="langgraph_writes",
            ttl=86400  # 24 hours TTL for automatic cleanup
        )
        logger.info("MongoDB checkpointer initialized")
    return _checkpointer


async def cleanup_checkpointer():
    """
    Clean up checkpointer resources.
    Should be called on application shutdown.
    """
    global _mongo_client, _checkpointer

    if _mongo_client is not None:
        try:
            await _mongo_client.close()  # type: ignore[misc]
            _mongo_client = None
            _checkpointer = None
            logger.info("Checkpointer and MongoDB client cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up checkpointer: {e}", exc_info=True)
