"""
Common message handler - Main router for non-command text messages.
Acts as a thin routing layer, delegating to specific handlers based on FSM state.
"""

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from app.models.user import User
from app.bot.states import ConversationMode, ReminderFlow, SettingsFlow
from app.bot.handlers.task import (
    process_nlp_task,
    handle_task_confirmation,
    handle_task_edit,
)
from app.bot.handlers.reminder import (
    process_reminder_input,
    handle_reminder_confirmation,
    handle_reminder_selection,
    handle_reminder_edit,
)
from app.bot.handlers.settings import (
    handle_timezone_setting,
    handle_api_key_setting,
    handle_ai_provider_selection,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()


@router.message(F.text & ~F.text.startswith("/"))
async def message_router(message: types.Message, state: FSMContext):
    """
    Main router for all non-command text messages.
    Routes messages to appropriate handlers based on current FSM state.

    Args:
        message: Telegram message object
        state: FSM context for state management
    """
    if message.from_user is None:
        return

    # Check if user is registered
    user = await User.find_one(User.telegram_id == message.from_user.id)

    if user is None:
        await message.answer(
            "You must first register yourself using /start command before using the bot."
        )
        return

    # Get current FSM state
    current_state = await state.get_state()
    logger.info(f"Message router called with state: {current_state}")

    # Route to appropriate handler based on state
    try:
        # Task-related states
        if current_state == ConversationMode.active or current_state is None:
            await process_nlp_task(message, state, user)

        elif current_state == ConversationMode.confirming_task:
            await handle_task_confirmation(message, state, user)

        elif current_state == ConversationMode.editing_task:
            await handle_task_edit(message, state, user)

        # Reminder-related states
        elif current_state == ReminderFlow.awaiting_reminder_input:
            await process_reminder_input(message, state, user)

        elif current_state == ReminderFlow.confirming_reminder:
            await handle_reminder_confirmation(message, state, user)

        elif current_state == ReminderFlow.selecting_task:
            await handle_reminder_selection(message, state, user)

        elif current_state == ReminderFlow.editing_reminder:
            await handle_reminder_edit(message, state, user)

        # Settings-related states
        elif current_state == SettingsFlow.awaiting_timezone:
            await handle_timezone_setting(message, state, user)

        elif current_state == SettingsFlow.awaiting_api_key:
            await handle_api_key_setting(message, state, user)

        elif current_state == SettingsFlow.selecting_default_ai:
            await handle_ai_provider_selection(message, state, user)

        else:
            # Unknown state - clear and inform user
            logger.warning(f"Unknown state encountered: {current_state}")
            await state.clear()
            await message.answer(
                "Something went wrong. Please use /start to begin again."
            )

    except Exception as e:
        logger.error(f"Error in message router: {e}", exc_info=True)
        await message.answer(
            "⚠️ An unexpected error occurred. Please try again or use /start to restart."
        )
