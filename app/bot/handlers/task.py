"""
Task-related message handlers.
Handles task creation, confirmation, and editing flows.
"""

from aiogram import types
from aiogram.fsm.context import FSMContext

from app.models.user import User
from app.bot.states import ConversationMode
from app.services import TaskService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Initialize service
task_service = TaskService()


async def process_nlp_task(message: types.Message, state: FSMContext, user: User):
    """
    Process natural language input as a task.
    Uses AI to parse task details from the text.

    Args:
        message: Telegram message object
        state: FSM context for state management
        user: User object
    """
    if message.from_user is None or message.text is None:
        return

    logger.info(f"Processing NLP task from user {message.from_user.id}: {message.text}")

    try:
        # Use the task service to process the input
        parsed_task = await task_service.process_task_from_nlp(message.text, user)

        if parsed_task:
            # Show parsed details to user for confirmation
            confirmation_text = (
                f"📝 I understood your task:\n\n"
                f"**Title:** {parsed_task.get('title', 'N/A')}\n"
                f"**Priority:** {parsed_task.get('priority', 'medium').title()}\n"
            )

            if parsed_task.get("due_date"):
                confirmation_text += f"**Due Date:** {parsed_task['due_date']}\n"
            if parsed_task.get("recurrence"):
                confirmation_text += f"**Recurrence:** {parsed_task['recurrence']}\n"

            confirmation_text += "\nWould you like me to create this task? (yes/no)"

            await message.answer(confirmation_text)

            # Store parsed task data and raw input in FSM
            await state.update_data(
                raw_task_input=message.text, parsed_task_data=parsed_task
            )
            await state.set_state(ConversationMode.confirming_task)
        else:
            # Parsing failed - ask user to rephrase
            await message.answer(
                "❓ I couldn't understand your task. Could you please rephrase it?\n\n"
                "Try including:\n"
                "• What you need to do\n"
                "• When you need to do it (optional)\n"
                "• Any other relevant details"
            )

    except Exception as e:
        logger.error(f"Error processing NLP task: {e}", exc_info=True)
        await message.answer(
            "⚠️ An error occurred while processing your task. Please try again."
        )


async def handle_task_confirmation(
    message: types.Message, state: FSMContext, user: User
):
    """
    Handle user confirmation of parsed task.

    Args:
        message: Telegram message object
        state: FSM context
        user: User object
    """
    if message.text is None:
        await message.answer("Please send a text response.")
        return

    user_response = message.text.lower().strip()

    if user_response in ["yes", "y", "yeah", "sure", "ok", "okay", "confirm"]:
        # Get stored task data
        data = await state.get_data()
        parsed_task_data = data.get("parsed_task_data", {})

        try:
            # Create the task using the service
            created_task = await task_service.create_task(user, parsed_task_data)

            # TODO: Once task creation is implemented, show task ID or details
            await message.answer(
                "✅ Task created successfully!\n\n"
                "You can send me another task anytime!"
            )

            logger.info(f"Task created successfully for user {user.telegram_id}")

        except Exception as e:
            logger.error(f"Error creating task: {e}", exc_info=True)
            await message.answer(
                "⚠️ An error occurred while creating your task. Please try again."
            )

        # Return to active state to accept new tasks
        await state.set_state(ConversationMode.active)

    elif user_response in ["no", "n", "nope", "cancel", "nah"]:
        await message.answer(
            "❌ Task cancelled. Feel free to send me a new task description!"
        )
        # Return to active state
        await state.set_state(ConversationMode.active)

    else:
        await message.answer("Please respond with 'yes' to confirm or 'no' to cancel.")


async def handle_task_edit(message: types.Message, state: FSMContext, user: User):
    """
    Handle editing task details.

    Args:
        message: Telegram message object
        state: FSM context
        user: User object
    """
    # TODO: Implement task editing logic
    # This will involve:
    # 1. Showing current task details
    # 2. Asking what to edit
    # 3. Processing the edits
    # 4. Updating the task in database

    await message.answer(
        "✏️ Task editing feature coming soon!\n\n"
        "For now, you can create a new task to replace it."
    )

    # Return to active state
    await state.set_state(ConversationMode.active)
