"""
Statistics handler - simple aggregation showcase.
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
    """Display user statistics using simple aggregation."""
    try:
        if not message.from_user:
            await message.answer("Unable to retrieve user information.")
            return

        user = await User.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Please use /start to register first.")
            return

        logger.info(f"Fetching statistics for user: {user.telegram_id}")

        # Simple aggregation using Beanie's count() method
        total_tasks = await Task.find(Task.user.id == user.id).count()  # type: ignore

        # Count completed tasks
        completed_tasks = await Task.find(
            Task.user.id == user.id,  # type: ignore
            Task.status == "done",
        ).count()

        # Count total reminders
        total_reminders = await Reminder.find(Reminder.user.id == user.id).count()  # type: ignore

        # Format and send message
        stats_message = "📊 <b>Your Statistics</b>\n\n"
        stats_message += f"📋 <b>Total Tasks:</b> {total_tasks}\n"
        stats_message += f"✅ <b>Completed Tasks:</b> {completed_tasks}\n"
        stats_message += f"🔔 <b>Total Reminders:</b> {total_reminders}\n"

        await message.answer(stats_message, parse_mode="HTML")
        logger.info(f"Statistics sent to user: {user.telegram_id}")

    except Exception as e:
        logger.error(f"Error in stats_handler: {e}", exc_info=True)
        await message.answer("An error occurred while fetching statistics.")
