from __future__ import annotations

from datetime import datetime
import inspect
from typing import Any, Dict, List, Literal, Optional, Type

from beanie import PydanticObjectId

from app.ai.services.timezone import convert_utc_to_user_timezone
from app.models.reminder import Reminder
from app.models.task import Task
from app.models.user import User
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def create_task(
    *,
    user_id: int,
    title: str,
    task_datetime: datetime,
    description: Optional[str] = None,
    priority: Literal["low", "medium", "high"] = "medium",
    tags: Optional[List[str]] = None,
    recurrence: Optional[str] = None,
    user_model: Type[User] = User,
    task_model: Type[Task] = Task,
) -> Dict[str, Any]:
    try:
        user = await user_model.get_by_telegram_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        task = task_model(
            user=user,  # type: ignore[arg-type]
            title=title,
            description=description,
            task_datetime=task_datetime,
            priority=priority,
            tags=tags or [],
            recurrence=recurrence,
            status="pending",
        )
        await task.insert()

        logger.info(f"Task created: {task.id} - {title}")
        task_dt_user_tz = convert_utc_to_user_timezone(task_datetime, user.timezone)
        return {
            "success": True,
            "task_id": str(task.id),
            "title": title,
            "task_datetime": task_dt_user_tz.isoformat(),  # type: ignore[union-attr]
            "message": f"✓ '{title}' created",
        }
    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def create_reminder(
    *,
    user_id: int,
    task_id: str,
    remind_at: datetime,
    message: Optional[str] = None,
    user_model: Type[User] = User,
    task_model: Type[Task] = Task,
    reminder_model: Type[Reminder] = Reminder,
) -> Dict[str, Any]:
    try:
        user = await user_model.get_by_telegram_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        task = await task_model.get(PydanticObjectId(task_id))
        if not task:
            return {"success": False, "error": "Task not found"}

        reminder = reminder_model(
            user=user,  # type: ignore[arg-type]
            task=task,  # type: ignore[arg-type]
            remind_at=remind_at,
            message=message,
            sent=False,
        )
        await reminder.insert()

        logger.info(f"Reminder created: {reminder.id} for task {task_id}")
        remind_at_user_tz = convert_utc_to_user_timezone(remind_at, user.timezone)
        return {
            "success": True,
            "reminder_id": str(reminder.id),
            "task_id": task_id,
            "remind_at": remind_at_user_tz.isoformat(),  # type: ignore[union-attr]
            "message": "✓ Reminder set",
        }
    except Exception as e:
        logger.error(f"Error creating reminder: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _get_owned_task(user_id: int, task_id: str, task_model: Type[Task]) -> Any:
    task = await task_model.get(PydanticObjectId(task_id))
    if not task:
        return None

    task_user = await task.user.fetch()  # type: ignore[union-attr]
    if task_user.telegram_id != user_id:  # type: ignore[union-attr]
        return None
    return task


async def edit_task(
    *,
    user_id: int,
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    task_datetime: Optional[datetime] = None,
    priority: Optional[Literal["low", "medium", "high"]] = None,
    tags: Optional[List[str]] = None,
    task_model: Type[Task] = Task,
) -> Dict[str, Any]:
    try:
        task = await _get_owned_task(user_id, task_id, task_model)
        if not task:
            return {"success": False, "error": "Task not found"}

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
            "message": "✓ Updated",
        }
    except Exception as e:
        logger.error(f"Error editing task: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def mark_task_done(
    *,
    user_id: int,
    task_id: str,
    task_model: Type[Task] = Task,
) -> Dict[str, Any]:
    try:
        task = await _get_owned_task(user_id, task_id, task_model)
        if not task:
            return {"success": False, "error": "Task not found"}

        await task.mark_as_done()
        logger.info(f"Task marked as done: {task_id}")
        return {"success": True, "task_id": task_id, "message": "✓ Done! 🎉"}
    except Exception as e:
        logger.error(f"Error marking task as done: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def delete_task(
    *,
    user_id: int,
    task_id: str,
    task_model: Type[Task] = Task,
    reminder_model: Type[Reminder] = Reminder,
) -> Dict[str, Any]:
    try:
        task = await _get_owned_task(user_id, task_id, task_model)
        if not task:
            return {"success": False, "error": "Task not found"}

        task_title = task.title
        reminders = await reminder_model.get_reminders_by_task(
            PydanticObjectId(task_id)
        )
        reminder_count = len(reminders)

        for reminder in reminders:
            await _maybe_await(reminder.delete())

        await _maybe_await(task.delete())

        logger.info(
            f"Task '{task_title}' (ID: {task_id}) deleted with {reminder_count} reminder(s) cascaded"
        )
        message = "✓ Deleted"
        if reminder_count > 0:
            message += (
                f" (+{reminder_count} reminder{'s' if reminder_count > 1 else ''})"
            )

        return {
            "success": True,
            "task_id": task_id,
            "reminders_deleted": reminder_count,
            "message": message,
        }
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def list_tasks(
    *,
    user_id: int,
    status: Optional[Literal["pending", "done"]] = None,
    limit: int = 10,
    user_model: Type[User] = User,
    task_model: Type[Task] = Task,
) -> Dict[str, Any]:
    try:
        user = await user_model.get_by_telegram_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        query = task_model.find(task_model.user.id == user.id)  # type: ignore[attr-defined]
        if status:
            query = query.find(task_model.status == status)

        tasks = await query.sort("-task_datetime").limit(limit).to_list()

        task_list = []
        for task in tasks:
            task_dt_user_tz = convert_utc_to_user_timezone(
                task.task_datetime, user.timezone
            )
            task_list.append(
                {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "task_datetime": task_dt_user_tz.isoformat(),  # type: ignore[union-attr]
                    "status": task.status,
                    "priority": task.priority,
                    "tags": task.tags,
                }
            )

        logger.info(
            f"Listed {len(task_list)} tasks for user {user_id} (times in {user.timezone})"
        )
        return {
            "success": True,
            "tasks": task_list,
            "count": len(task_list),
            "message": f"{len(task_list)} task{'s' if len(task_list) != 1 else ''}",
        }
    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def get_task_statistics(
    *,
    user_id: int,
    user_model: Type[User] = User,
    task_model: Type[Task] = Task,
) -> Dict[str, Any]:
    try:
        user = await user_model.get_by_telegram_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        stats = await task_model.get_task_statistics(user.id)  # type: ignore[arg-type]
        logger.info(f"Retrieved task statistics for user {user_id}")
        return {"success": True, "statistics": stats, "message": "✓ Stats"}
    except Exception as e:
        logger.error(f"Error getting task statistics: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
