"""
Reminder model with cascade deletion support.

CASCADE DELETION (automatic via BackLink):
- When a Task is deleted: All its Reminders are automatically deleted
- When a User is deleted: All Tasks are deleted, which cascades to delete all Reminders

The cascade is handled automatically by Beanie's BackLink relationships defined in Task and User models.
"""

from __future__ import annotations

from beanie import Document, Link, PydanticObjectId
from pydantic import Field
from datetime import datetime
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from app.utils.logger import setup_logger

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.task import Task

logger = setup_logger(__name__)


class Reminder(Document):
    task: Link["Task"]
    user: Link["User"]
    remind_at: datetime
    message: Optional[str] = None
    sent: bool = False
    recurrence: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "reminders"
        use_state_management = True
        indexes = [
            "user",
            "task",
            "remind_at",
            "sent",
        ]

    # ==================== Business Logic Methods ====================

    async def mark_as_sent(self) -> "Reminder":
        """Mark this reminder as sent."""
        self.sent = True
        self.updated_at = datetime.utcnow()
        await self.save()
        logger.info(f"Reminder marked as sent: {self.id}")
        return self

    async def reschedule(self, new_time: datetime) -> "Reminder":
        """Reschedule this reminder to a new time."""
        self.remind_at = new_time
        self.sent = False
        self.updated_at = datetime.utcnow()
        await self.save()
        logger.info(f"Reminder rescheduled: {self.id} to {new_time}")
        return self

    # ==================== Aggregation Pipeline Methods ====================

    @classmethod
    async def get_pending_reminders(cls, user_id: PydanticObjectId) -> List["Reminder"]:
        """
        Get all pending (unsent) reminders for a user using aggregation.

        Args:
            user_id: User's ObjectId

        Returns:
            List of pending reminders sorted by remind_at
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "user.$id": user_id,
                        "sent": False,
                    }
                },
                {"$sort": {"remind_at": 1}},
            ]

            results = await cls.aggregate(pipeline, projection_model=Reminder).to_list()
            return results
        except Exception as e:
            logger.error(f"Error getting pending reminders: {e}", exc_info=True)
            return []

    @classmethod
    async def get_due_reminders(cls, before_time: Optional[datetime] = None) -> List["Reminder"]:
        """
        Get all reminders that are due (remind_at <= current time) and not sent.

        Args:
            before_time: Optional cutoff time, defaults to now

        Returns:
            List of due reminders
        """
        try:
            cutoff = before_time or datetime.utcnow()
            pipeline = [
                {
                    "$match": {
                        "sent": False,
                        "remind_at": {"$lte": cutoff},
                    }
                },
                {"$sort": {"remind_at": 1}},
            ]

            results = await cls.aggregate(pipeline, projection_model=Reminder).to_list()
            logger.info(f"Found {len(results)} due reminders")
            return results
        except Exception as e:
            logger.error(f"Error getting due reminders: {e}", exc_info=True)
            return []

    @classmethod
    async def get_upcoming_reminders(
        cls,
        user_id: PydanticObjectId,
        limit: int = 5,
    ) -> List["Reminder"]:
        """
        Get upcoming reminders for a user using aggregation.

        Args:
            user_id: User's ObjectId
            limit: Maximum number of reminders to return

        Returns:
            List of upcoming reminders
        """
        try:
            now = datetime.utcnow()
            pipeline = [
                {
                    "$match": {
                        "user.$id": user_id,
                        "sent": False,
                        "remind_at": {"$gte": now},
                    }
                },
                {"$sort": {"remind_at": 1}},
                {"$limit": limit},
            ]

            results = await cls.aggregate(pipeline, projection_model=Reminder).to_list()
            return results
        except Exception as e:
            logger.error(f"Error getting upcoming reminders: {e}", exc_info=True)
            return []

    @classmethod
    async def get_reminder_statistics(cls, user_id: PydanticObjectId) -> Dict[str, Any]:
        """
        Get reminder statistics for a user using aggregation pipeline.

        Returns:
            Dictionary with reminder statistics
        """
        try:
            pipeline = [
                {"$match": {"user.$id": user_id}},
                {
                    "$group": {
                        "_id": "$sent",
                        "count": {"$sum": 1},
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": "$count"},
                        "by_status": {
                            "$push": {
                                "sent": "$_id",
                                "count": "$count",
                            }
                        },
                    }
                },
            ]

            result = await cls.aggregate(pipeline).to_list()

            if result:
                return result[0]

            return {"total": 0, "by_status": []}
        except Exception as e:
            logger.error(f"Error getting reminder statistics: {e}", exc_info=True)
            return {"total": 0, "by_status": []}

    @classmethod
    async def get_reminders_by_task(cls, task_id: PydanticObjectId) -> List["Reminder"]:
        """
        Get all reminders for a specific task.

        Args:
            task_id: Task's ObjectId

        Returns:
            List of reminders for the task
        """
        try:
            # Query reminders where task Link points to the given task_id
            results = await cls.find({"task.$id": task_id}).sort("+remind_at").to_list()
            return results  # type: ignore
        except Exception as e:
            logger.error(f"Error getting reminders by task: {e}", exc_info=True)
            return []

    @classmethod
    async def get_reminders_by_date_range(
        cls,
        user_id: PydanticObjectId,
        start_date: datetime,
        end_date: datetime,
    ) -> List["Reminder"]:
        """
        Get reminders within a date range using aggregation.

        Args:
            user_id: User's ObjectId
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of reminders within the date range
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "user.$id": user_id,
                        "remind_at": {"$gte": start_date, "$lte": end_date},
                    }
                },
                {"$sort": {"remind_at": 1}},
            ]

            results = await cls.aggregate(pipeline, projection_model=Reminder).to_list()
            return results
        except Exception as e:
            logger.error(f"Error getting reminders by date range: {e}", exc_info=True)
            return []

    # ==================== Convenience Methods for Telegram ID ====================

    @classmethod
    async def get_pending_for_user(cls, telegram_id: int) -> List["Reminder"]:
        """Get all pending reminders for a user - convenient for aiogram handlers"""
        from app.models.user import User

        user = await User.find_one(User.telegram_id == telegram_id)
        if not user:
            return []

        return await cls.get_pending_reminders(user.id)  # type: ignore

    @classmethod
    async def get_upcoming(cls, telegram_id: int, limit: int = 5) -> List["Reminder"]:
        """Get upcoming reminders for a user sorted by remind_at"""
        from app.models.user import User

        user = await User.find_one(User.telegram_id == telegram_id)
        if not user:
            return []

        return await cls.get_upcoming_reminders(user.id, limit)  # type: ignore

    @classmethod
    async def create_for_task(
        cls,
        task_id: str,
        remind_at: datetime,
        message: Optional[str] = None,
        recurrence: Optional[str] = None,
    ) -> "Reminder":
        """Create reminder for a task - convenient for aiogram FSM handlers"""
        from app.models.task import Task

        task = await Task.get(task_id)
        if not task:
            raise ValueError(f"Task with id {task_id} not found")

        await task.fetch_link(Task.user)

        reminder = cls(
            task=task,  # type: ignore
            user=task.user,  # type: ignore
            remind_at=remind_at,
            message=message,
            recurrence=recurrence,
        )
        await reminder.insert()
        logger.info(f"Reminder created for task {task_id}: {reminder.id}")
        return reminder

