"""
Task Service for task management operations.
Handles task creation, updates, deletion, and queries.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.task import Task
from app.models.user import User
from app.services.nlp_service import NLPService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TaskService:
    """Service for managing tasks."""

    def __init__(self):
        self.nlp_service = NLPService()

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

    async def create_task(
        self, user: User, task_data: Dict[str, Any]
    ) -> Optional[Task]:
        """
        Create a new task in the database.

        Args:
            user: User object
            task_data: Dictionary with task details

        Returns:
            Created Task object or None if creation failed
        """
        logger.info(f"Creating task for user {user.telegram_id}")

        try:
            # TODO: Implement actual task creation
            # task = Task(
            #     user_id=user.id,
            #     title=task_data.get('title'),
            #     description=task_data.get('description'),
            #     due_date=task_data.get('due_date'),
            #     priority=task_data.get('priority', 'medium'),
            #     recurrence=task_data.get('recurrence'),
            #     status='pending'
            # )
            # await task.insert()

            logger.info("Task created successfully (placeholder)")
            return None  # Return task object once implemented

        except Exception as e:
            logger.error(f"Error creating task: {e}", exc_info=True)
            return None

    async def get_user_tasks(
        self, user: User, status: Optional[str] = None
    ) -> List[Task]:
        """
        Get all tasks for a user, optionally filtered by status.

        Args:
            user: User object
            status: Optional status filter ('pending', 'completed', etc.)

        Returns:
            List of Task objects
        """
        logger.info(f"Fetching tasks for user {user.telegram_id}")

        try:
            # TODO: Implement task retrieval
            # query = Task.find(Task.user_id == user.id)
            # if status:
            #     query = query.find(Task.status == status)
            # tasks = await query.to_list()

            return []  # Return actual tasks once implemented

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
            # TODO: Implement task update
            # task = await Task.get(task_id)
            # if task:
            #     for key, value in updates.items():
            #         setattr(task, key, value)
            #     await task.save()
            #     return task

            return None

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
            # TODO: Implement task deletion
            # task = await Task.get(task_id)
            # if task:
            #     await task.delete()
            #     return True

            return False

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
        return await self.update_task(
            task_id, {"status": "completed", "completed_at": datetime.utcnow()}
        )
