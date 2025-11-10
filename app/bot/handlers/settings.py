"""
Settings-related message handlers.
Handles settings configuration via webapp.
"""

from aiogram import types
from aiogram.fsm.context import FSMContext

from app.models.user import User
from app.bot.states import SettingsFlow
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def handle_timezone_setting(
    message: types.Message, state: FSMContext, user: User
):
    """
    Handle timezone setting.
    Timezone configuration is done via webapp, not text input.

    Args:
        message: Telegram message object
        state: FSM context
        user: User object
    """
    await message.answer(
        "⚙️ Timezone configuration is handled via the settings webapp.\n\n"
        "Use /start to open settings."
    )


async def handle_api_key_setting(message: types.Message, state: FSMContext, user: User):
    """
    Handle API key setting.
    API key configuration is done via webapp, not text input (for security).

    Args:
        message: Telegram message object
        state: FSM context
        user: User object
    """
    await message.answer(
        "🔑 API key configuration is handled via the settings webapp.\n\n"
        "Please click the 'Configure Settings' or 'Settings' button to open the webapp.\n\n"
        "If you've already configured your settings, the bot should have confirmed it. "
        "If not, use /start to try again."
    )


async def handle_ai_provider_selection(
    message: types.Message, state: FSMContext, user: User
):
    """
    Handle AI provider selection.
    AI provider selection is done via webapp, not text input.

    Args:
        message: Telegram message object
        state: FSM context
        user: User object
    """
    await message.answer(
        "🤖 AI provider selection is handled via the settings webapp.\n\n"
        "Use /start to open settings."
    )
