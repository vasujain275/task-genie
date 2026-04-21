"""
Statistics handler - simple aggregation showcase.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.application.services.stats import StatsService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()
stats_service = StatsService()


@router.message(Command("stats"))
async def stats_handler(message: Message):
    """Display user statistics using simple aggregation."""
    try:
        if not message.from_user:
            await message.answer("Unable to retrieve user information.")
            return

        statistics = await stats_service.get_user_statistics(message.from_user.id)
        if not statistics:
            await message.answer("Please use /start to register first.")
            return

        logger.info(f"Fetching statistics for user: {message.from_user.id}")

        # Format and send message
        stats_message = "📊 <b>Your Statistics</b>\n\n"
        stats_message += f"📋 <b>Total Tasks:</b> {statistics.total_tasks}\n"
        stats_message += f"✅ <b>Completed Tasks:</b> {statistics.completed_tasks}\n"
        stats_message += f"🔔 <b>Total Reminders:</b> {statistics.total_reminders}\n"

        await message.answer(stats_message, parse_mode="HTML")
        logger.info(f"Statistics sent to user: {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in stats_handler: {e}", exc_info=True)
        await message.answer("An error occurred while fetching statistics.")
