"""
User model with manual cascade deletion support.

CASCADE DELETION CHAIN:
User -> Tasks -> Reminders

When a user is deleted using delete_with_cascade():
1. All tasks linked to this user are manually deleted
2. Each task deletion manually deletes its associated reminders
3. This ensures no orphaned data in the database

Manual cascade is used to avoid Pydantic circular dependency issues with BackLinks.
"""

from __future__ import annotations

from beanie import Document
from typing import Optional
from datetime import datetime
from pydantic import Field
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class User(Document):
    telegram_id: int  # Keep as telegram_id for clarity
    name: str
    username: Optional[str] = None  # Telegram username
    openai_key: Optional[str] = None
    timezone: str = "UTC"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        use_state_management = True
        indexes = [
            "telegram_id",  # Index for fast lookups
        ]

    @classmethod
    async def get_or_create(
        cls, telegram_id: int, name: str, username: Optional[str] = None
    ):
        """Get user by telegram_id or create if not exists - convenient for aiogram handlers"""
        try:
            user = await cls.find_one(cls.telegram_id == telegram_id)
            if not user:
                logger.info(f"Creating new user: {telegram_id}")
                user = cls(telegram_id=telegram_id, name=name, username=username)
                await user.insert()
                logger.info(f"User created successfully: {telegram_id}")
            else:
                logger.debug(f"User found: {telegram_id}")
            return user
        except Exception as e:
            logger.error(
                f"Error in get_or_create for user {telegram_id}: {e}", exc_info=True
            )
            raise

    @classmethod
    async def get_by_telegram_id(cls, telegram_id: int):
        """Get user by telegram_id - convenient for aiogram handlers"""
        try:
            logger.debug(f"Fetching user by telegram_id: {telegram_id}")
            return await cls.find_one(cls.telegram_id == telegram_id)
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {e}", exc_info=True)
            raise

    async def delete_with_cascade(self) -> dict:
        """
        Delete user with manual cascade deletion of all related data.

        Cascade chain:
        User -> Tasks -> Reminders

        Manually deletes all tasks, and each task deletion cascades to its reminders.

        Returns:
            Dictionary with deletion counts
        """
        from app.models.task import Task
        from app.models.reminder import Reminder

        # Find all tasks for this user
        tasks = await Task.find(Task.user.id == self.id).to_list()  # type: ignore
        task_count = len(tasks)
        reminder_count = 0

        # Delete each task and its reminders manually
        for task in tasks:
            # Find and delete reminders for this task
            reminders = await Reminder.get_reminders_by_task(task.id)  # type: ignore
            reminder_count += len(reminders)

            for reminder in reminders:
                await reminder.delete()

            # Delete the task
            await task.delete()

        # Delete the user
        await self.delete()

        logger.info(
            f"User {self.telegram_id} deleted with manual cascade deletion of "
            f"{task_count} task(s) and {reminder_count} reminder(s)"
        )

        return {
            "user_id": self.telegram_id,
            "tasks_deleted": task_count,
            "reminders_deleted": reminder_count,
            "message": f"User account deleted with {task_count} task(s) and {reminder_count} reminder(s)",
        }
