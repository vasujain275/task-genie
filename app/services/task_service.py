"""
Task Service for task management operations.
Handles task creation, updates, deletion, and queries.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from beanie import PydanticObjectId

from app.models.task import Task
from app.models.user import User
from app.services.nlp_service import NLPService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TaskService:
    """Service for managing tasks with business logic."""

    def __init__(self):
        self.nlp_service = NLPService()

    # ==================== NLP Integration ====================

    async def process_task_from_nlp(
        self, raw_text: str, user: User
    ) -> Optional[Dict[str, Any]]:
        """
        Process raw text input to extract task details using NLP.

        Args:
            raw_text: The raw text from user
            user: User object

        Returns:
            Dictionary with parsed task details or None if parsing failed
        """
        logger.info(f"Processing task from NLP for user {user.telegram_id}")

        try:
            parsed_data = await self.nlp_service.parse_task_from_text(raw_text, user)

            if parsed_data:
                logger.info(f"Successfully parsed task: {parsed_data.get('title')}")
                return parsed_data
            else:
                logger.warning("Failed to parse task from text")
                return None

        except Exception as e:
            logger.error(f"Error processing task from NLP: {e}", exc_info=True)
            return None

    # ==================== CRUD Operations ====================

    async def create_task(
        self, user: User, task_data: Dict[str, Any]
    ) -> Optional[Task]:
        """
        Create a new task in the database.

        Args:
            user: User object
            task_data: Dictionary with task details (title, description, task_datetime, priority, etc.)

        Returns:
            Created Task object or None if creation failed
        """
        logger.info(f"Creating task for user {user.telegram_id}")

        try:
            # Validate required fields
            if not task_data.get("title") or not task_data.get("task_datetime"):
                logger.error("Missing required fields: title or task_datetime")
                return None

            task = Task(
                user=user,  # type: ignore
                title=str(task_data["title"]),
                description=task_data.get("description"),
                task_datetime=task_data["task_datetime"],
                priority=task_data.get("priority", "medium"),
                recurrence=task_data.get("recurrence"),
                tags=task_data.get("tags", []),
            )
            await task.insert()
            logger.info(f"Task created successfully: {task.id}")
            return task

        except Exception as e:
            logger.error(f"Error creating task: {e}", exc_info=True)
            return None

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task object or None if not found
        """
        try:
            task = await Task.get(task_id)
            if task:
                await task.fetch_link(Task.user)
            return task
        except Exception as e:
            logger.error(f"Error fetching task {task_id}: {e}", exc_info=True)
            return None

    async def get_user_tasks(
        self,
        user: User,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        skip: int = 0,
    ) -> List[Task]:
        """
        Get all tasks for a user, optionally filtered by status.

        Args:
            user: User object
            status: Optional status filter ('pending', 'done')
            limit: Optional limit on results
            skip: Number of results to skip

        Returns:
            List of Task objects
        """
        logger.info(f"Fetching tasks for user {user.telegram_id}")

        try:
            query = Task.find(Task.user.ref.id == user.id)
            if status:
                query = query.find(Task.status == status)

            query = query.sort("-task_datetime").skip(skip)
            if limit:
                query = query.limit(limit)

            tasks = await query.to_list()
            logger.info(f"Found {len(tasks)} tasks for user {user.telegram_id}")
            return tasks

        except Exception as e:
            logger.error(f"Error fetching tasks: {e}", exc_info=True)
            return []

    async def update_task(
        self, task_id: str, updates: Dict[str, Any]
    ) -> Optional[Task]:
        """
        Update an existing task.

        Args:
            task_id: ID of the task to update
            updates: Dictionary of fields to update

        Returns:
            Updated Task object or None if update failed
        """
        logger.info(f"Updating task {task_id}")

        try:
            task = await Task.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found for update")
                return None

            # Update timestamp
            updates["updated_at"] = datetime.utcnow()

            # Update fields
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            await task.save()
            logger.info(f"Task updated successfully: {task_id}")
            return task

        except Exception as e:
            logger.error(f"Error updating task: {e}", exc_info=True)
            return None

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: ID of the task to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.info(f"Deleting task {task_id}")

        try:
            task = await Task.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found for deletion")
                return False

            await task.delete()
            logger.info(f"Task deleted successfully: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting task: {e}", exc_info=True)
            return False

    async def mark_task_complete(self, task_id: str) -> Optional[Task]:
        """
        Mark a task as completed.

        Args:
            task_id: ID of the task to complete

        Returns:
            Updated Task object or None if update failed
        """
        logger.info(f"Marking task {task_id} as complete")
        task = await Task.get(task_id)
        if task:
            return await task.mark_as_done()
        return None

    async def mark_task_pending(self, task_id: str) -> Optional[Task]:
        """
        Mark a task as pending.

        Args:
            task_id: ID of the task to mark as pending

        Returns:
            Updated Task object or None if update failed
        """
        logger.info(f"Marking task {task_id} as pending")
        task = await Task.get(task_id)
        if task:
            return await task.mark_as_pending()
        return None

    # ==================== Advanced Query Operations ====================

    async def get_overdue_tasks(self, user: User) -> List[Task]:
        """
        Get all overdue tasks for a user.

        Args:
            user: User object

        Returns:
            List of overdue Task objects
        """
        logger.info(f"Fetching overdue tasks for user {user.telegram_id}")

        try:
            tasks = await Task.get_overdue_tasks(user.id)  # type: ignore
            logger.info(f"Found {len(tasks)} overdue tasks")
            return tasks
        except Exception as e:
            logger.error(f"Error fetching overdue tasks: {e}", exc_info=True)
            return []

    async def get_tasks_by_date_range(
        self,
        user: User,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Task]:
        """
        Get tasks within a date range.

        Args:
            user: User object
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of Task objects within the date range
        """
        logger.info(f"Fetching tasks for user {user.telegram_id} from {start_date} to {end_date}")

        try:
            tasks = await Task.get_tasks_by_date_range(user.id, start_date, end_date)  # type: ignore
            logger.info(f"Found {len(tasks)} tasks in date range")
            return tasks
        except Exception as e:
            logger.error(f"Error fetching tasks by date range: {e}", exc_info=True)
            return []

    async def search_tasks(self, user: User, search_term: str) -> List[Task]:
        """
        Search tasks by title or description.

        Args:
            user: User object
            search_term: Search term

        Returns:
            List of matching Task objects
        """
        logger.info(f"Searching tasks for user {user.telegram_id} with term: {search_term}")

        try:
            tasks = await Task.search_tasks(user.id, search_term)  # type: ignore
            logger.info(f"Found {len(tasks)} matching tasks")
            return tasks
        except Exception as e:
            logger.error(f"Error searching tasks: {e}", exc_info=True)
            return []

    async def get_task_statistics(self, user: User) -> Dict[str, Any]:
        """
        Get task statistics for a user.

        Args:
            user: User object

        Returns:
            Dictionary with task statistics
        """
        logger.info(f"Fetching task statistics for user {user.telegram_id}")

        try:
            stats = await Task.get_task_statistics(user.id)  # type: ignore
            return stats
        except Exception as e:
            logger.error(f"Error fetching task statistics: {e}", exc_info=True)
            return {"total": 0, "by_status": []}

    async def get_today_tasks(self, user: User) -> List[Task]:
        """
        Get tasks for today.

        Args:
            user: User object

        Returns:
            List of tasks for today
        """
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return await self.get_tasks_by_date_range(user, start_of_day, end_of_day)

    async def get_week_tasks(self, user: User) -> List[Task]:
        """
        Get tasks for the current week.

        Args:
            user: User object

        Returns:
            List of tasks for this week
        """
        now = datetime.utcnow()
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)

        return await self.get_tasks_by_date_range(user, start_of_week, end_of_week)

