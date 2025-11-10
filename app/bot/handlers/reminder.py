"""
Reminder-related utility functions and helpers.
Most reminder logic is now handled by LangGraph AI agent in common.py
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.models.reminder import Reminder
from app.models.user import User
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Default reminder time before task due date
DEFAULT_REMINDER_MINUTES = 15


async def create_reminder_in_db(
    user: User,
    task_id: str,
    reminder_data: Dict[str, Any]
) -> Optional[Reminder]:
    """
    Create a reminder directly in MongoDB.
    This is called by the LangGraph agent after parsing user input.

    Args:
        user: User object
        task_id: ID of the task to set reminder for
        reminder_data: Dictionary containing:
            - reminder_time: datetime (required)
            - message: str (optional, defaults to task title)
            - recurrence: str (optional)

    Returns:
        Created Reminder object or None if creation failed
    """
    logger.info(f"Creating reminder in DB for user {user.telegram_id}, task {task_id}")

    try:
        # TODO: Implement actual reminder creation in MongoDB
        # reminder = Reminder(
        #     user_id=user.id,
        #     task_id=task_id,
        #     reminder_time=reminder_data['reminder_time'],
        #     message=reminder_data.get('message', ''),
        #     recurrence=reminder_data.get('recurrence'),
        #     is_active=True,
        #     created_at=datetime.now()
        # )
        # await reminder.insert()
        # logger.info(f"Reminder created successfully with ID: {reminder.id}")
        # return reminder

        logger.info("Reminder creation placeholder - implement MongoDB integration")
        return None

    except Exception as e:
        logger.error(f"Error creating reminder in DB: {e}", exc_info=True)
        return None


async def update_reminder_in_db(
    reminder_id: str,
    updates: Dict[str, Any]
) -> Optional[Reminder]:
    """
    Update an existing reminder in MongoDB.
    This is called by the LangGraph agent for conversational updates like:
    - "No, remind me 30 min earlier"
    - "Change it to 1 hour before"

    Args:
        reminder_id: ID of the reminder to update
        updates: Dictionary of fields to update (e.g., reminder_time, message)

    Returns:
        Updated Reminder object or None if update failed
    """
    logger.info(f"Updating reminder {reminder_id} with: {updates}")

    try:
        # TODO: Implement actual reminder update in MongoDB
        # reminder = await Reminder.get(reminder_id)
        # if reminder:
        #     for key, value in updates.items():
        #         setattr(reminder, key, value)
        #     reminder.updated_at = datetime.now()
        #     await reminder.save()
        #     logger.info(f"Reminder {reminder_id} updated successfully")
        #     return reminder

        logger.info("Reminder update placeholder - implement MongoDB integration")
        return None

    except Exception as e:
        logger.error(f"Error updating reminder: {e}", exc_info=True)
        return None


async def get_user_reminders(
    user: User,
    task_id: Optional[str] = None,
    active_only: bool = True
) -> list:
    """
    Retrieve user's reminders from MongoDB.

    Args:
        user: User object
        task_id: Optional task ID to filter reminders for specific task
        active_only: If True, only return active reminders

    Returns:
        List of Reminder objects
    """
    logger.info(f"Fetching reminders for user {user.telegram_id}")

    try:
        # TODO: Implement actual reminder retrieval from MongoDB
        # query = Reminder.find(Reminder.user_id == user.id)
        #
        # if task_id:
        #     query = query.find(Reminder.task_id == task_id)
        # if active_only:
        #     query = query.find(Reminder.is_active == True)
        #
        # reminders = await query.to_list()
        # logger.info(f"Found {len(reminders)} reminders")
        # return reminders

        logger.info("Reminder retrieval placeholder - implement MongoDB integration")
        return []

    except Exception as e:
        logger.error(f"Error fetching reminders: {e}", exc_info=True)
        return []


def calculate_reminder_time(due_date: datetime, minutes_before: int = DEFAULT_REMINDER_MINUTES) -> datetime:
    """
    Calculate reminder time based on task due date.

    Args:
        due_date: Task due date/time
        minutes_before: Minutes before due date to set reminder (default: 15)

    Returns:
        Calculated reminder datetime
    """
    return due_date - timedelta(minutes=minutes_before)


async def delete_reminder_in_db(reminder_id: str) -> bool:
    """
    Delete or deactivate a reminder.

    Args:
        reminder_id: ID of the reminder to delete

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Deleting reminder {reminder_id}")

    try:
        # TODO: Implement actual reminder deletion in MongoDB
        # reminder = await Reminder.get(reminder_id)
        # if reminder:
        #     # Option 1: Soft delete
        #     reminder.is_active = False
        #     await reminder.save()
        #
        #     # Option 2: Hard delete
        #     # await reminder.delete()
        #
        #     logger.info(f"Reminder {reminder_id} deleted successfully")
        #     return True

        logger.info("Reminder deletion placeholder - implement MongoDB integration")
        return False

    except Exception as e:
        logger.error(f"Error deleting reminder: {e}", exc_info=True)
        return False
