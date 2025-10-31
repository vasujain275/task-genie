from beanie import Document, Link
from pydantic import Field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.task import Task


class Reminder(Document):
    task: Link["Task"]
    user: Link["User"]
    remind_at: datetime
    sent: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reminders"
        use_state_management = True

    @classmethod
    async def get_pending_for_user(cls, telegram_id: int):
        """Get all pending reminders for a user - convenient for aiogram handlers"""
        from app.models.user import User

        user = await User.find_one(User.telegram_id == telegram_id)
        if not user:
            return []

        return await cls.find(cls.user.ref.id == user.id, cls.sent == False).to_list()

    @classmethod
    async def get_upcoming(cls, telegram_id: int, limit: int = 5):
        """Get upcoming reminders for a user sorted by remind_at"""
        from app.models.user import User

        user = await User.find_one(User.telegram_id == telegram_id)
        if not user:
            return []

        return (
            await cls.find(cls.user.ref.id == user.id, cls.sent == False)
            .sort("+remind_at")
            .limit(limit)
            .to_list()
        )

    @classmethod
    async def create_for_task(cls, task_id: str, remind_at: datetime):
        """Create reminder for a task - convenient for aiogram FSM handlers"""
        from app.models.task import Task

        task = await Task.get(task_id)
        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        await task.fetch_link(Task.user)  # Fetch the user relationship

        reminder = cls(
            task=task,  # type: ignore - Beanie handles Link conversion
            user=task.user,  # type: ignore
            remind_at=remind_at,
        )
        await reminder.insert()
        return reminder
