from aiogram import Bot
from aiogram.types import BotCommand
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def set_bot_commands_menu(my_bot: Bot) -> None:
    # Register commands for Telegram bot (menu)
    commands = [
        BotCommand(command="/start", description="Start or reconfigure bot"),
        BotCommand(command="/settings", description="View and update settings"),
        BotCommand(command="/stats", description="View your task and reminders stats"),
    ]
    try:
        await my_bot.set_my_commands(commands)
        logger.info("Bot commands menu set successfully")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}", exc_info=True)
