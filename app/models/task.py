from beanie import Document, Link, PydanticObjectId
from typing import Optional, Literal, TYPE_CHECKING, List, Dict, Any
from pydantic import Field
from datetime import datetime
from app.utils.logger import setup_logger

if TYPE_CHECKING:
    from app.models.user import User

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

    # ==================== Aggregation Pipeline Methods ====================

    @classmethod
    async def get_task_statistics(cls, user_id: PydanticObjectId) -> Dict[str, Any]:
        """
        Get task statistics for a user using aggregation pipeline.

        Returns:
            Dictionary with task statistics
        """
        try:
            pipeline = [
                {"$match": {"user.$id": user_id}},
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1},
                        "priorities": {"$push": "$priority"},
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": "$count"},
                        "by_status": {
                            "$push": {
                                "status": "$_id",
                                "count": "$count",
                                "priorities": "$priorities",
                            }
                        },
                    }
                },
            ]

            result = await cls.aggregate(pipeline).to_list()

            if result:
                stats = result[0]
                # Process priorities
                for status_group in stats.get("by_status", []):
                    priorities = status_group.get("priorities", [])
                    status_group["priority_breakdown"] = {
                        "low": sum(1 for p in priorities if p == "low"),
                        "medium": sum(1 for p in priorities if p == "medium"),
                        "high": sum(1 for p in priorities if p == "high"),
                    }
                    del status_group["priorities"]

                return stats

            return {"total": 0, "by_status": []}
        except Exception as e:
            logger.error(f"Error getting task statistics: {e}", exc_info=True)
            return {"total": 0, "by_status": []}

    @classmethod
    async def get_tasks_by_date_range(
        cls,
        user_id: PydanticObjectId,
        start_date: datetime,
        end_date: datetime,
    ) -> List["Task"]:
        """
        Get tasks within a date range using aggregation.

        Args:
            user_id: User's ObjectId
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of tasks within the date range
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "user.$id": user_id,
                        "task_datetime": {"$gte": start_date, "$lte": end_date},
                    }
                },
                {"$sort": {"task_datetime": 1}},
            ]

            results = await cls.aggregate(pipeline, projection_model=Task).to_list()
            return results
        except Exception as e:
            logger.error(f"Error getting tasks by date range: {e}", exc_info=True)
            return []

    @classmethod
    async def get_overdue_tasks(cls, user_id: PydanticObjectId) -> List["Task"]:
        """
        Get overdue tasks for a user using aggregation.

        Args:
            user_id: User's ObjectId

        Returns:
            List of overdue tasks
        """
        try:
            now = datetime.utcnow()
            pipeline = [
                {
                    "$match": {
                        "user.$id": user_id,
                        "status": "pending",
                        "task_datetime": {"$lt": now},
                    }
                },
                {"$sort": {"task_datetime": 1}},
            ]

            results = await cls.aggregate(pipeline, projection_model=Task).to_list()
            return results
        except Exception as e:
            logger.error(f"Error getting overdue tasks: {e}", exc_info=True)
            return []

    @classmethod
    async def search_tasks(
        cls,
        user_id: PydanticObjectId,
        search_term: str,
    ) -> List["Task"]:
        """
        Search tasks by title or description using aggregation.

        Args:
            user_id: User's ObjectId
            search_term: Term to search for

        Returns:
            List of matching tasks
        """
        try:
            pipeline = [
                {"$match": {"user.$id": user_id}},
                {
                    "$match": {
                        "$or": [
                            {"title": {"$regex": search_term, "$options": "i"}},
                            {"description": {"$regex": search_term, "$options": "i"}},
                        ]
                    }
                },
                {"$sort": {"task_datetime": -1}},
            ]

            results = await cls.aggregate(pipeline, projection_model=Task).to_list()
            return results
        except Exception as e:
            logger.error(f"Error searching tasks: {e}", exc_info=True)
            return []

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

