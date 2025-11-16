"""
Natural language conversation handler for task creation
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.models.user import User
from app.bot.states import ConversationMode, TaskCreationStates
from app.bot.keyboards.inline import get_task_confirmation_keyboard
from app.ai.nlp_service import get_nlp_service
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()


@router.message(
    StateFilter(ConversationMode.active),
    F.text & ~F.text.startswith("/")
)
async def handle_natural_language_message(message: Message, state: FSMContext):
    """
    Handle natural language messages when in active conversation mode.

    This is the main entry point for task creation via natural language.
    Parses the message and either asks for confirmation or reports errors.
    """
    try:
        # Get user
        if not message.from_user:
            await message.answer("User information not available.")
            return

        user = await User.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("User not found. Please use /start to register.")
            return

        # Check if user has configured OpenAI key
        if not user.openai_key:
            await message.answer(
                "⚠️ Please configure your OpenAI API key first.\n\n"
                "Use the button below or send /settings to configure your API key.",
            )
            return

        if not message.text:
            await message.answer("Please send a text message.")
            return

        logger.info(f"Processing NL message from user {user.telegram_id}: {message.text}")

        # Show typing indicator
        await message.bot.send_chat_action(message.chat.id, "typing")  # type: ignore[union-attr]

        # Get NLP service
        nlp_service = await get_nlp_service()

        # Process the message
        result = await nlp_service.process_message(
            user_id=user.telegram_id,
            user_message=message.text,
            user_name=user.name,
            user_timezone=user.timezone
        )

        # Handle result
        if result.get("error"):
            # Error occurred
            await message.answer(result["response_message"])

        elif result.get("needs_confirmation"):
            # Task parsed, need confirmation
            await state.set_state(TaskCreationStates.confirming_task)

            # Store task data in state for potential editing
            # Convert datetime objects to strings for JSON serialization
            task_data = result.get("task_data")
            reminder_data = result.get("reminder_data")

            # Serialize task_data
            if task_data:
                task_data_serialized = {
                    "title": task_data.get("title"),
                    "description": task_data.get("description"),
                    "task_datetime": task_data["task_datetime"].isoformat() if task_data.get("task_datetime") else None,
                    "priority": task_data.get("priority"),
                    "tags": task_data.get("tags"),
                    "recurrence": task_data.get("recurrence")
                }
            else:
                task_data_serialized = None

            # Serialize reminder_data
            if reminder_data:
                reminder_data_serialized = {
                    "remind_at": reminder_data["remind_at"].isoformat() if reminder_data.get("remind_at") else None,
                    "message": reminder_data.get("message"),
                    "recurrence": reminder_data.get("recurrence")
                }
            else:
                reminder_data_serialized = None

            await state.update_data(
                task_data=task_data_serialized,
                reminder_data=reminder_data_serialized
            )

            await message.answer(
                result["confirmation_message"],
                parse_mode="Markdown",
                reply_markup=get_task_confirmation_keyboard()
            )

        elif result.get("task_created"):
            # Task created successfully (shouldn't happen on first message, but handle it)
            await message.answer(result["response_message"], parse_mode="Markdown")
            await state.set_state(ConversationMode.active)

        else:
            # Unknown state
            await message.answer("Something went wrong. Please try again.")

    except Exception as e:
        logger.error(f"Error in handle_natural_language_message: {e}", exc_info=True)
        await message.answer(
            "An error occurred while processing your message. Please try again."
        )
        await state.set_state(ConversationMode.active)


@router.message(StateFilter(TaskCreationStates.confirming_task))
async def handle_task_confirmation(message: Message, state: FSMContext):
    """
    Handle user response to task confirmation request.

    Accepts:
    - "yes", "y", "confirm", "ok", "sure" -> confirm and create task
    - "no", "cancel" -> cancel task creation
    - Anything else -> attempt to re-parse as modification request
    """
    try:
        if not message.text or not message.from_user:
            await message.answer("Invalid message.")
            return

        user_response = message.text.lower().strip()

        # Get user
        user = await User.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("User not found. Please use /start to register.")
            await state.clear()
            return

        logger.info(f"Task confirmation response from user {user.telegram_id}: {user_response}")

        # Check for confirmation
        if user_response in ["yes", "y", "confirm", "ok", "okay", "sure", "yep", "yeah"]:
            # User confirmed - create the task
            await message.bot.send_chat_action(message.chat.id, "typing")  # type: ignore[union-attr]

            nlp_service = await get_nlp_service()
            result = await nlp_service.confirm_task(user.telegram_id)

            if result.get("task_created"):
                await message.answer(result["response_message"], parse_mode="Markdown")
                await state.set_state(ConversationMode.active)
            else:
                await message.answer(
                    result.get("response_message", "Failed to create task. Please try again.")
                )
                await state.set_state(ConversationMode.active)

        elif user_response in ["no", "n", "cancel", "nope", "nah"]:
            # User cancelled
            await message.answer(
                "Task creation cancelled. What else can I help you with?"
            )
            await state.set_state(ConversationMode.active)

        else:
            # User wants to modify - treat as new task input
            await message.answer(
                "Got it! Let me parse that as a new task..."
            )
            await state.set_state(ConversationMode.active)

            # Re-process the message as a new task
            # User's next message will trigger the handler
            # (We don't re-send here to avoid recursion)

    except Exception as e:
        logger.error(f"Error in handle_task_confirmation: {e}", exc_info=True)
        await message.answer(
            "An error occurred. Please try again or use /start to restart."
        )
        await state.set_state(ConversationMode.active)


@router.message(StateFilter(TaskCreationStates.editing_task_details))
async def handle_task_editing(message: Message, state: FSMContext):
    """
    Handle task editing requests (future enhancement).

    For now, treats as a new task input.
    """
    try:
        if not message.from_user or not message.text:
            await message.answer("Invalid message.")
            return

        logger.info(f"Task editing from user {message.from_user.id}")        # For now, just process as new task
        await state.set_state(ConversationMode.active)
        await message.answer(
            "Let me process that as a new task..."
        )

        # This will trigger handle_natural_language_message
        user = await User.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("User not found. Please use /start to register.")
            return

        nlp_service = await get_nlp_service()
        result = await nlp_service.process_message(
            user_id=user.telegram_id,
            user_message=message.text,
            user_name=user.name,
            user_timezone=user.timezone
        )

        if result.get("needs_confirmation"):
            await state.set_state(TaskCreationStates.confirming_task)
            await message.answer(
                result["confirmation_message"],
                parse_mode="Markdown"
            )
        else:
            await message.answer(result.get("response_message", "Please try again."))

    except Exception as e:
        logger.error(f"Error in handle_task_editing: {e}", exc_info=True)
        await message.answer("An error occurred. Please try again.")
        await state.set_state(ConversationMode.active)


# Callback query handlers for inline buttons (future enhancement)
@router.callback_query(F.data == "confirm_task")
async def callback_confirm_task(callback: CallbackQuery, state: FSMContext):
    """Handle inline button confirmation (future enhancement)"""
    await callback.answer()

    try:
        if not callback.from_user or not callback.message:
            return

        user = await User.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.message.edit_text("User not found. Please use /start to register.")  # type: ignore[union-attr]
            return

        nlp_service = await get_nlp_service()
        result = await nlp_service.confirm_task(user.telegram_id)

        if result.get("task_created"):
            await callback.message.edit_text(  # type: ignore[union-attr]
                result["response_message"],
                parse_mode="Markdown"
            )
            await state.set_state(ConversationMode.active)
        else:
            await callback.message.edit_text(  # type: ignore[union-attr]
                result.get("response_message", "Failed to create task.")
            )
            await state.set_state(ConversationMode.active)

    except Exception as e:
        logger.error(f"Error in callback_confirm_task: {e}", exc_info=True)
        if callback.message:
            await callback.message.edit_text("An error occurred. Please try again.")  # type: ignore[union-attr]
        await state.set_state(ConversationMode.active)


@router.callback_query(F.data == "cancel_task")
async def callback_cancel_task(callback: CallbackQuery, state: FSMContext):
    """Handle inline button cancellation (future enhancement)"""
    await callback.answer()

    try:
        if callback.message:
            await callback.message.edit_text(  # type: ignore[union-attr]
                "Task creation cancelled. What else can I help you with?"
            )
        await state.set_state(ConversationMode.active)

    except Exception as e:
        logger.error(f"Error in callback_cancel_task: {e}", exc_info=True)
        if callback.message:
            await callback.message.edit_text("An error occurred.")  # type: ignore[union-attr]
        await state.set_state(ConversationMode.active)
