"""
Task-related utility functions and helpers.
Most task logic is now handled by LangGraph AI agent in common.py
"""

from typing import Optional, Dict, Any
from app.models.task import Task
from app.models.user import User
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def create_task_in_db(user: User, task_data: Dict[str, Any]) -> Optional[Task]:
    """
    Create a task directly in MongoDB.
    This is called by the LangGraph agent after parsing user input.

    Args:
        user: User object
        task_data: Dictionary containing:
            - title: str (required)
            - description: str (optional)
            - due_date: datetime (optional)
            - priority: str (optional, default: 'medium')
            - recurrence: str (optional)
            - tags: list[str] (optional)

    Returns:
        Created Task object or None if creation failed
    """
    logger.info(f"Creating task in DB for user {user.telegram_id}: {task_data.get('title')}")

    try:
        # TODO: Implement actual task creation in MongoDB
        # task = Task(
        #     user_id=user.id,
        #     title=task_data['title'],
        #     description=task_data.get('description', ''),
        #     due_date=task_data.get('due_date'),
        #     priority=task_data.get('priority', 'medium'),
        #     recurrence=task_data.get('recurrence'),
        #     tags=task_data.get('tags', []),
        #     status='pending',
        #     created_at=datetime.now()
        # )
        # await task.insert()
        # logger.info(f"Task created successfully with ID: {task.id}")
        # return task

        logger.info("Task creation placeholder - implement MongoDB integration")
        return None

    except Exception as e:
        logger.error(f"Error creating task in DB: {e}", exc_info=True)
        return None


async def update_task_in_db(task_id: str, updates: Dict[str, Any]) -> Optional[Task]:
    """
    Update an existing task in MongoDB.
    This is called by the LangGraph agent for conversational updates.

    Args:
        task_id: ID of the task to update
        updates: Dictionary of fields to update

    Returns:
        Updated Task object or None if update failed
    """
    logger.info(f"Updating task {task_id} with: {updates}")

    try:
        # TODO: Implement actual task update in MongoDB
        # task = await Task.get(task_id)
        # if task:
        #     for key, value in updates.items():
        #         setattr(task, key, value)
        #     task.updated_at = datetime.now()
        #     await task.save()
        #     logger.info(f"Task {task_id} updated successfully")
        #     return task

        logger.info("Task update placeholder - implement MongoDB integration")
        return None

    except Exception as e:
        logger.error(f"Error updating task: {e}", exc_info=True)
        return None


async def get_user_tasks(user: User, filters: Optional[Dict[str, Any]] = None) -> list:
    """
    Retrieve user's tasks from MongoDB with optional filters.
    This is called by the LangGraph agent for queries like "show my tasks for today".

    Args:
        user: User object
        filters: Optional filters:
            - status: str ('pending', 'completed', etc.)
            - due_date: datetime or date range
            - priority: str
            - tags: list[str]

    Returns:
        List of Task objects
    """
    logger.info(f"Fetching tasks for user {user.telegram_id} with filters: {filters}")

    try:
        # TODO: Implement actual task retrieval from MongoDB
        # query = Task.find(Task.user_id == user.id)
        #
        # if filters:
        #     if 'status' in filters:
        #         query = query.find(Task.status == filters['status'])
        #     if 'priority' in filters:
        #         query = query.find(Task.priority == filters['priority'])
        #     if 'due_date' in filters:
        #         # Handle date range queries
        #         pass
        #
        # tasks = await query.to_list()
        # logger.info(f"Found {len(tasks)} tasks")
        # return tasks

        logger.info("Task retrieval placeholder - implement MongoDB integration")
        return []

    except Exception as e:
        logger.error(f"Error fetching tasks: {e}", exc_info=True)
        return []

