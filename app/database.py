from pymongo import AsyncMongoClient
from beanie import init_beanie
from app.models.task import Task
from app.models.reminder import Reminder
from app.models.user import User
from app.config import settings


async def init_db():
    # Create Async PyMongo client
    client = AsyncMongoClient(settings.MONGO_URI)

    # Init beanie with the Product document class
    await init_beanie(database=client[settings.MONGO_DB_NAME], document_models=[User, Task, Reminder])
