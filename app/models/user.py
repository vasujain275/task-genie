"""
User model with cascade deletion support.

CASCADE DELETION CHAIN:
User -> Tasks -> Reminders

When a user is deleted using delete_with_cascade() or delete(link_rule=DeleteRules.DELETE_LINKS):
1. All tasks linked to this user are deleted
2. Each task deletion cascades to delete its associated reminders
3. This ensures no orphaned data in the database

The cascade is handled automatically by Beanie's BackLink relationships.
"""

from __future__ import annotations

from beanie import Document, BackLink, DeleteRules
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from pydantic import Field
from app.utils.logger import setup_logger

if TYPE_CHECKING:
    from app.models.task import Task

logger = setup_logger(__name__)


class User(Document):
    telegram_id: int  # Keep as telegram_id for clarity
    name: str
    username: Optional[str] = None  # Telegram username
    openai_key: Optional[str] = None
    timezone: str = "UTC"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # BackLink to tasks for cascade deletion support
    # When user is deleted, all their tasks (and their reminders) will be deleted
    tasks: List[BackLink["Task"]] = Field(
        default_factory=list,
        json_schema_extra={"original_field": "user"}
    )

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
        Delete user with cascade deletion of all related data.

        Cascade chain:
        User -> Tasks -> Reminders

        This uses Beanie's built-in DeleteRules.DELETE_LINKS to:
        1. Delete all tasks associated with this user
        2. Each task deletion cascades to delete its reminders

        Returns:
            Dictionary with deletion counts
        """
        # Fetch tasks to get count before deletion
        task_count = len(self.tasks) if hasattr(self, 'tasks') and self.tasks else 0

        # Delete user with cascade to all linked tasks (which will cascade to reminders)
        await self.delete(link_rule=DeleteRules.DELETE_LINKS)

        logger.info(
            f"User {self.telegram_id} deleted with cascade deletion of "
            f"{task_count} task(s) and their associated reminders"
        )

        return {
            "user_id": self.telegram_id,
            "tasks_deleted": task_count,
            "message": f"User account deleted with {task_count} task(s) and all associated reminders"
        }
