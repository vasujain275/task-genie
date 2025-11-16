"""
Task management tools for the LLM agent
"""

from typing import Optional, List, Literal, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from beanie import PydanticObjectId
from pymongo import DESCENDING

from app.models.task import Task
from app.models.reminder import Reminder
from app.models.user import User
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


# ==================== Helper Functions ====================

def convert_utc_to_user_timezone(dt: datetime, user_timezone: str) -> datetime:
    """
    Convert UTC datetime to user's timezone.

    Args:
        dt: Datetime in UTC (naive or aware)
        user_timezone: User's timezone (e.g., "Asia/Kolkata")

    Returns:
        Datetime in user's timezone (aware)
    """
    if dt is None:
        return None  # type: ignore[return-value]

    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    # Convert to user timezone
    user_tz = ZoneInfo(user_timezone)
    return dt.astimezone(user_tz)


# ==================== Tool Input Schemas ====================

class CreateTaskInput(BaseModel):
    """Input for creating a task"""
    user_id: int = Field(description="Telegram user ID (auto-injected, do not specify)")
    title: str = Field(description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    task_datetime: datetime = Field(description="When the task is due/scheduled")
    priority: Literal["low", "medium", "high"] = Field("medium", description="Task priority")
    tags: List[str] = Field(default_factory=list, description="Task tags/categories")
    recurrence: Optional[str] = Field(None, description="Recurrence pattern (daily, weekly, etc.)")


class CreateReminderInput(BaseModel):
    """Input for creating a reminder for a task"""
    user_id: int = Field(description="Telegram user ID (auto-injected, do not specify)")
    task_id: str = Field(description="Task ID to attach reminder to")
    remind_at: datetime = Field(description="When to send the reminder")
    message: Optional[str] = Field(None, description="Custom reminder message")


class EditTaskInput(BaseModel):
    """Input for editing a task"""
    user_id: int = Field(description="Telegram user ID (auto-injected, do not specify)")
    task_id: str = Field(description="Task ID to edit")
    title: Optional[str] = Field(None, description="New task title")
    description: Optional[str] = Field(None, description="New task description")
    task_datetime: Optional[datetime] = Field(None, description="New task datetime")
    priority: Optional[Literal["low", "medium", "high"]] = Field(None, description="New priority")
    tags: Optional[List[str]] = Field(None, description="New tags")


class MarkTaskDoneInput(BaseModel):
    """Input for marking a task as done"""
    user_id: int = Field(description="Telegram user ID (auto-injected, do not specify)")
    task_id: str = Field(description="Task ID to mark as done")


class DeleteTaskInput(BaseModel):
    """Input for deleting a task"""
    user_id: int = Field(description="Telegram user ID (auto-injected, do not specify)")
    task_id: str = Field(description="Task ID to delete")


class ListTasksInput(BaseModel):
    """Input for listing tasks"""
    user_id: int = Field(description="Telegram user ID (auto-injected, do not specify)")
    status: Optional[Literal["pending", "done"]] = Field(None, description="Filter by status")
    limit: int = Field(10, description="Maximum number of tasks to return")


class GetTaskStatsInput(BaseModel):
    """Input for getting task statistics"""
    user_id: int = Field(description="Telegram user ID (auto-injected, do not specify)")


# ==================== Tools ====================

@tool(args_schema=CreateTaskInput)
async def create_task(
    user_id: int,
    title: str,
    task_datetime: datetime,
    description: Optional[str] = None,
    priority: Literal["low", "medium", "high"] = "medium",
    tags: Optional[List[str]] = None,
    recurrence: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new task for the user.

    Returns a dictionary with task_id and success status.
    """
    try:
        # Get user
        user = await User.get_by_telegram_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        # Create task
        task = Task(
            user=user,  # type: ignore[arg-type]
            title=title,
            description=description,
            task_datetime=task_datetime,
            priority=priority,
            tags=tags or [],
            recurrence=recurrence,
            status='pending'
        )
        await task.insert()

        logger.info(f"Task created: {task.id} - {title}")

        # Convert datetime to user timezone for response
        task_dt_user_tz = convert_utc_to_user_timezone(task_datetime, user.timezone)

        return {
            "success": True,
            "task_id": str(task.id),
            "title": title,
            "task_datetime": task_dt_user_tz.isoformat(),  # In user timezone
            "message": f"Task '{title}' created successfully!"
        }

    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(args_schema=CreateReminderInput)
async def create_reminder(
    user_id: int,
    task_id: str,
    remind_at: datetime,
    message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a reminder for an existing task.

    Returns a dictionary with reminder_id and success status.
    """
    try:
        # Get user
        user = await User.get_by_telegram_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        # Get task
        task = await Task.get(PydanticObjectId(task_id))
        if not task:
            return {"success": False, "error": "Task not found"}

        # Create reminder
        reminder = Reminder(
            user=user,  # type: ignore[arg-type]
            task=task,  # type: ignore[arg-type]
            remind_at=remind_at,
            message=message,
            sent=False
        )
        await reminder.insert()

        logger.info(f"Reminder created: {reminder.id} for task {task_id}")

        # Convert remind_at to user timezone for response
        remind_at_user_tz = convert_utc_to_user_timezone(remind_at, user.timezone)

        return {
            "success": True,
            "reminder_id": str(reminder.id),
            "task_id": task_id,
            "remind_at": remind_at_user_tz.isoformat(),  # In user timezone
            "message": f"Reminder set for {remind_at_user_tz.strftime('%I:%M %p on %B %d')}"
        }

    except Exception as e:
        logger.error(f"Error creating reminder: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(args_schema=EditTaskInput)
async def edit_task(
    user_id: int,
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    task_datetime: Optional[datetime] = None,
    priority: Optional[Literal["low", "medium", "high"]] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Edit an existing task. Only provided fields will be updated.

    Returns a dictionary with success status and updated fields.
    """
    try:
        # Get task
        task = await Task.get(PydanticObjectId(task_id))
        if not task:
            return {"success": False, "error": "Task not found"}

        # Verify ownership
        task_user = await task.user.fetch()  # type: ignore[union-attr]
        if task_user.telegram_id != user_id:  # type: ignore[union-attr]
            return {"success": False, "error": "Task not found"}

        # Update fields
        updated_fields = []
        if title is not None:
            task.title = title
            updated_fields.append("title")
        if description is not None:
            task.description = description
            updated_fields.append("description")
        if task_datetime is not None:
            task.task_datetime = task_datetime
            updated_fields.append("datetime")
        if priority is not None:
            task.priority = priority
            updated_fields.append("priority")
        if tags is not None:
            task.tags = tags
            updated_fields.append("tags")

        task.updated_at = datetime.utcnow()
        await task.save()

        logger.info(f"Task updated: {task_id} - fields: {updated_fields}")

        return {
            "success": True,
            "task_id": task_id,
            "updated_fields": updated_fields,
            "message": f"Task '{task.title}' updated successfully!"
        }

    except Exception as e:
        logger.error(f"Error editing task: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(args_schema=MarkTaskDoneInput)
async def mark_task_done(user_id: int, task_id: str) -> Dict[str, Any]:
    """
    Mark a task as done/completed.

    Returns a dictionary with success status.
    """
    try:
        # Get task
        task = await Task.get(PydanticObjectId(task_id))
        if not task:
            return {"success": False, "error": "Task not found"}

        # Verify ownership
        task_user = await task.user.fetch()  # type: ignore[union-attr]
        if task_user.telegram_id != user_id:  # type: ignore[union-attr]
            return {"success": False, "error": "Task not found"}

        # Mark as done
        await task.mark_as_done()

        logger.info(f"Task marked as done: {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "message": f"Task '{task.title}' marked as done! 🎉"
        }

    except Exception as e:
        logger.error(f"Error marking task as done: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(args_schema=DeleteTaskInput)
async def delete_task(user_id: int, task_id: str) -> Dict[str, Any]:
    """
    Delete a task permanently with manual cascade deletion of reminders.

    Manually deletes all associated reminders before deleting the task
    to ensure no orphaned data.

    Returns a dictionary with success status.
    """
    try:
        # Get task
        task = await Task.get(PydanticObjectId(task_id))
        if not task:
            return {"success": False, "error": "Task not found"}

        # Verify ownership
        task_user = await task.user.fetch()  # type: ignore[union-attr]
        if task_user.telegram_id != user_id:  # type: ignore[union-attr]
            return {"success": False, "error": "Task not found"}

        task_title = task.title

        # Manually cascade delete: Find and delete all reminders for this task
        reminders = await Reminder.get_reminders_by_task(PydanticObjectId(task_id))
        reminder_count = len(reminders)

        for reminder in reminders:
            await reminder.delete()

        # Delete the task
        await task.delete()

        logger.info(f"Task '{task_title}' (ID: {task_id}) deleted with {reminder_count} reminder(s) cascaded")

        message = f"Task '{task_title}' deleted successfully!"
        if reminder_count > 0:
            message += f" ({reminder_count} associated reminder(s) also deleted)"

        return {
            "success": True,
            "task_id": task_id,
            "reminders_deleted": reminder_count,
            "message": message
        }

    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
@tool(args_schema=ListTasksInput)
async def list_tasks(
    user_id: int,
    status: Optional[Literal["pending", "done"]] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    List user's tasks, optionally filtered by status.

    Returns a list of tasks with their details (datetimes in user's timezone).
    """
    try:
        # Get user
        user = await User.get_by_telegram_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        # Build query
        query = Task.find(Task.user.id == user.id)  # type: ignore[attr-defined]

        if status:
            query = query.find(Task.status == status)

        # Get tasks sorted by datetime descending
        tasks = await query.sort("-task_datetime").limit(limit).to_list()

        # Format tasks - convert datetimes to user timezone
        task_list = []
        for task in tasks:
            # Convert task datetime to user timezone
            task_dt_user_tz = convert_utc_to_user_timezone(task.task_datetime, user.timezone)

            task_list.append({
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "task_datetime": task_dt_user_tz.isoformat(),  # In user timezone
                "status": task.status,
                "priority": task.priority,
                "tags": task.tags
            })

        logger.info(f"Listed {len(task_list)} tasks for user {user_id} (times in {user.timezone})")

        return {
            "success": True,
            "tasks": task_list,
            "count": len(task_list),
            "message": f"Found {len(task_list)} task(s)"
        }

    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(args_schema=GetTaskStatsInput)
async def get_task_statistics(user_id: int) -> Dict[str, Any]:
    """
    Get task statistics for the user (total, pending, done, by priority, etc.).

    Returns a dictionary with various statistics.
    """
    try:
        # Get user
        user = await User.get_by_telegram_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        # Get statistics using aggregation
        stats = await Task.get_task_statistics(user.id)  # type: ignore[arg-type]

        logger.info(f"Retrieved task statistics for user {user_id}")

        return {
            "success": True,
            "statistics": stats,
            "message": "Task statistics retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error getting task statistics: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# Export all tools
TASK_TOOLS = [
    create_task,
    create_reminder,
    edit_task,
    mark_task_done,
    delete_task,
    list_tasks,
    get_task_statistics
]
