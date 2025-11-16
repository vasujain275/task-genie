"""
Statistics handler with aggregation functions showcase.

Demonstrates MongoDB aggregation operations:
- $group, $sum, $count
- $cond (conditional aggregation)
- Multiple pipeline stages
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.models import User, Task, Reminder
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()


@router.message(Command("stats"))
async def stats_handler(message: Message):
    """
    Display user statistics using MongoDB aggregation.

    Showcases:
    - Task counts by status ($group, $sum, $cond)
    - Priority distribution ($group)
    - Reminder counts
    """
    try:
        if not message.from_user:
            await message.answer("Unable to retrieve user information.")
            return

        user = await User.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Please use /start to register first.")
            return

        logger.info(f"Fetching statistics for user: {user.telegram_id}")

        # Get statistics using aggregation
        task_stats = await get_task_stats(user.id)  # type: ignore
        reminder_count = await get_reminder_count(user.id)  # type: ignore

        # Format and send message
        stats_message = format_stats_message(task_stats, reminder_count)
        await message.answer(stats_message, parse_mode="HTML")
        logger.info(f"Statistics sent to user: {user.telegram_id}")

    except Exception as e:
        logger.error(f"Error in stats_handler: {e}", exc_info=True)
        await message.answer("An error occurred while fetching statistics.")


async def get_task_stats(user_id) -> dict:
    """
    Aggregation: Get comprehensive task statistics in a single pipeline.

    Demonstrates:
    - $match: Filtering by user
    - $group: Multiple aggregations
    - $sum: Counting total tasks
    - $cond: Conditional counting (status, priority)
    """
    try:
        pipeline = [
            {"$match": {"user.$id": user_id}},
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    # Count by status
                    "completed": {
                        "$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}
                    },
                    "pending": {
                        "$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}
                    },
                    # Count by priority
                    "high_priority": {
                        "$sum": {"$cond": [{"$eq": ["$priority", "high"]}, 1, 0]}
                    },
                    "medium_priority": {
                        "$sum": {"$cond": [{"$eq": ["$priority", "medium"]}, 1, 0]}
                    },
                    "low_priority": {
                        "$sum": {"$cond": [{"$eq": ["$priority", "low"]}, 1, 0]}
                    },
                }
            },
        ]

        results = await Task.aggregate(pipeline).to_list()

        if results:
            data = results[0]
            total = data.get("total", 0)
            completed = data.get("completed", 0)

            return {
                "total": total,
                "completed": completed,
                "pending": data.get("pending", 0),
                "completion_rate": round((completed / total * 100), 1)
                if total > 0
                else 0,
                "high_priority": data.get("high_priority", 0),
                "medium_priority": data.get("medium_priority", 0),
                "low_priority": data.get("low_priority", 0),
            }

        return {
            "total": 0,
            "completed": 0,
            "pending": 0,
            "completion_rate": 0,
            "high_priority": 0,
            "medium_priority": 0,
            "low_priority": 0,
        }
    except Exception as e:
        logger.error(f"Error in get_task_stats: {e}", exc_info=True)
        return {
            "total": 0,
            "completed": 0,
            "pending": 0,
            "completion_rate": 0,
            "high_priority": 0,
            "medium_priority": 0,
            "low_priority": 0,
        }


async def get_reminder_count(user_id) -> int:
    """
    Aggregation: Simple count of total reminders.

    Demonstrates: $match, $count
    """
    try:
        pipeline = [
            {"$match": {"user.$id": user_id}},
            {"$count": "total"},
        ]

        results = await Reminder.aggregate(pipeline).to_list()
        return results[0]["total"] if results else 0
    except Exception as e:
        logger.error(f"Error in get_reminder_count: {e}", exc_info=True)
        return 0


def format_stats_message(task_stats: dict, reminder_count: int) -> str:
    """Format statistics into a clean, readable message."""

    msg = "📊 <b>Your Statistics</b>\n\n"

    # Task overview
    msg += "📋 <b>Tasks</b>\n"
    msg += f"  • Total: {task_stats['total']}\n"
    msg += f"  • Completed: {task_stats['completed']} ✅\n"
    msg += f"  • Pending: {task_stats['pending']} ⏳\n"
    msg += f"  • Completion Rate: {task_stats['completion_rate']}%\n\n"

    # Priority breakdown
    msg += "🎯 <b>By Priority</b>\n"
    msg += f"  • High: {task_stats['high_priority']} 🔴\n"
    msg += f"  • Medium: {task_stats['medium_priority']} 🟡\n"
    msg += f"  • Low: {task_stats['low_priority']} 🟢\n\n"

    # Reminders
    msg += f"🔔 <b>Reminders:</b> {reminder_count}\n"

    return msg
