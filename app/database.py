from beanie import init_beanie
from app.models import User,Task,Reminder
from app.config import settings
from motor.motor_asyncio import AsyncIOMotorClient


async def init_db(client: AsyncIOMotorClient):
    """Initializes the database connection and sets up Beanie with the document models."""

    await init_beanie(database=client.get_database(settings.MONGO_DB_NAME), document_models=[User, Task, Reminder])  # type: ignore
