"""
Task model with manual cascade deletion support.

CASCADE DELETION:
- When a Task is deleted: All associated Reminders are manually deleted
- When a User is deleted: All Tasks are manually deleted, which cascades to Reminders

Manual cascade is used to avoid Pydantic circular dependency issues with BackLinks.
"""

from __future__ import annotations

from beanie import Document, Link, PydanticObjectId
from typing import Optional, Literal, TYPE_CHECKING, List, Dict, Any
from pydantic import Field
from datetime import datetime
from app.utils.logger import setup_logger

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.reminder import Reminder

logger = setup_logger(__name__)


class Task(Document):
    user: Link["User"]
    title: str
    description: Optional[str] = None
    task_datetime: datetime
    recurrence: Optional[str] = None
    status: Literal["pending", "done"] = "pending"
    priority: Literal["low", "medium", "high"] = "medium"
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "tasks"
        use_state_management = True
        indexes = [
            "user",
            "status",
            "task_datetime",
            "priority",
        ]

    # ==================== Business Logic Repository Methods ====================

    async def mark_as_done(self) -> "Task":
        """Mark this task as done."""
        self.status = "done"
        self.updated_at = datetime.utcnow()
        await self.save()
        logger.info(f"Task marked as done: {self.id}")
        return self

    async def mark_as_pending(self) -> "Task":
        """Mark this task as pending."""
        self.status = "pending"
        self.updated_at = datetime.utcnow()
        await self.save()
        logger.info(f"Task marked as pending: {self.id}")
        return self

    # ==================== Convenience Methods for Telegram ID ====================

    @classmethod
    async def create_for_user(
        cls,
        telegram_id: int,
        title: str,
        task_datetime: datetime,
        description: Optional[str] = None,
        recurrence: Optional[str] = None,
        priority: Literal["low", "medium", "high"] = "medium",
        tags: Optional[List[str]] = None,
    ) -> "Task":
        """Create task for user by telegram_id - convenient for aiogram FSM handlers"""
        from app.models.user import User

        user = await User.find_one(User.telegram_id == telegram_id)
        if not user:
            raise ValueError(f"User with telegram_id {telegram_id} not found")

        task = cls(
            user=user,  # type: ignore
            title=title,
            description=description,
            task_datetime=task_datetime,
            recurrence=recurrence,
            priority=priority,
            tags=tags or [],
        )
        await task.insert()
        logger.info(f"Task created for telegram_id {telegram_id}: {task.id}")
        return task

