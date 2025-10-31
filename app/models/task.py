from beanie import Document, Link, BackLink
from typing import Optional, Literal, TYPE_CHECKING
from pydantic import Field
from datetime import datetime

if TYPE_CHECKING:
    from app.models.user import User


class Task(Document):
    user: Link["User"]  # Proper relationship with User model
    title: str
    description: Optional[str] = None
    task_datetime: datetime
    recurrence: Optional[str] = None
    status: Literal["pending", "done"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "tasks"
        use_state_management = True

    @classmethod
    async def get_user_tasks(cls, telegram_id: int, status: Optional[str] = None):
        """Get all tasks for a user by telegram_id - convenient for aiogram handlers"""
        from app.models.user import User

        user = await User.find_one(User.telegram_id == telegram_id)
        if not user:
            return []

        query = cls.find(cls.user.ref.id == user.id)
        if status:
            query = query.find(cls.status == status)
        return await query.to_list()

    @classmethod
    async def create_for_user(
        cls,
        telegram_id: int,
        title: str,
        task_datetime: datetime,
        description: Optional[str] = None,
        recurrence: Optional[str] = None,
    ):
        """Create task for user by telegram_id - convenient for aiogram FSM handlers"""
        from app.models.user import User

        user = await User.find_one(User.telegram_id == telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        task = cls(
            user=user,  # type: ignore - Beanie handles Link conversion
            title=title,
            description=description,
            task_datetime=task_datetime,
            recurrence=recurrence,
        )
        await task.insert()
        return task
