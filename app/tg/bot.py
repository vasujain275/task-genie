from aiogram import Bot
from aiogram.types import BotCommand


async def set_bot_commands_menu(my_bot: Bot) -> None:
    # Register commands for Telegram bot (menu)
    commands = [
        BotCommand(command="/id", description="👋 Get my ID"),
        BotCommand(command="/start",description="Start Chatting!")
    ]
    try:
        await my_bot.set_my_commands(commands)
    except Exception as e:
        # logger.error(f"Can't set commands - {e}")
        print(e)
