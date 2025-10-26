from beanie import Document, Link
from pydantic import Field
from datetime import datetime
from app.models.user import User
from app.models.task import Task


class Reminder(Document):
    task: Link[Task]
    user: Link[User]
    remind_at: datetime
    sent: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reminders"
