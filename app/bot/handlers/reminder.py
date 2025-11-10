"""
Reminder-related message handlers.
Handles reminder creation, confirmation, and management flows.
"""

from aiogram import types
from aiogram.fsm.context import FSMContext

from app.models.user import User
from app.bot.states import ReminderFlow, ConversationMode
from app.services import ReminderService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Initialize service
reminder_service = ReminderService()


async def process_reminder_input(message: types.Message, state: FSMContext, user: User):
    """
    Process reminder details from user input.

    Args:
        message: Telegram message object
        state: FSM context
        user: User object
    """
    if message.text is None:
        await message.answer("Please send a text message with reminder details.")
        return

    logger.info(
        f"Processing reminder input from user {user.telegram_id}: {message.text}"
    )

    try:
        # Use the reminder service to process the input
        parsed_reminder = await reminder_service.process_reminder_from_nlp(
            message.text, user
        )

        if parsed_reminder:
            # Show parsed details to user for confirmation
            confirmation_text = f"⏰ **Reminder Details:**\n\n"
            confirmation_text += (
                f"**Message:** {parsed_reminder.get('message', 'N/A')}\n"
            )

            if parsed_reminder.get("time"):
                confirmation_text += f"**Time:** {parsed_reminder['time']}\n"
            if parsed_reminder.get("recurrence"):
                confirmation_text += (
                    f"**Recurrence:** {parsed_reminder['recurrence']}\n"
                )

            confirmation_text += "\nConfirm? (yes/no)"

            await message.answer(confirmation_text)

            # Store parsed data in FSM
            await state.update_data(
                reminder_input=message.text, parsed_reminder_data=parsed_reminder
            )
            await state.set_state(ReminderFlow.confirming_reminder)
        else:
            # Parsing failed
            await message.answer(
                "❓ I couldn't understand your reminder. Please try again.\n\n"
                "Example: 'Remind me to call mom at 5pm tomorrow'"
            )

    except Exception as e:
        logger.error(f"Error processing reminder input: {e}", exc_info=True)
        await message.answer(
            "⚠️ An error occurred while processing your reminder. Please try again."
        )


async def handle_reminder_confirmation(
    message: types.Message, state: FSMContext, user: User
):
    """
    Handle reminder confirmation.

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
        # Get stored reminder data
        data = await state.get_data()
        parsed_reminder_data = data.get("parsed_reminder_data", {})

        try:
            # Create the reminder using the service
            created_reminder = await reminder_service.create_reminder(
                user, parsed_reminder_data
            )

            # TODO: Once reminder creation is implemented, schedule it
            # if created_reminder:
            #     await reminder_service.schedule_reminder(created_reminder)

            await message.answer(
                "✅ Reminder set successfully!\n\n"
                "You'll be notified at the scheduled time."
            )

            logger.info(f"Reminder created successfully for user {user.telegram_id}")

        except Exception as e:
            logger.error(f"Error creating reminder: {e}", exc_info=True)
            await message.answer(
                "⚠️ An error occurred while setting your reminder. Please try again."
            )

        # Return to active state
        await state.set_state(ConversationMode.active)
    else:
        await message.answer("❌ Reminder cancelled.")
        # Return to active state
        await state.set_state(ConversationMode.active)


async def handle_reminder_selection(
    message: types.Message, state: FSMContext, user: User
):
    """
    Handle task selection for reminder.

    Args:
        message: Telegram message object
        state: FSM context
        user: User object
    """
    # TODO: Implement task selection logic
    await message.answer(
        "📋 Please select a task from the list above or use /start to cancel."
    )


async def handle_reminder_edit(message: types.Message, state: FSMContext, user: User):
    """
    Handle reminder time editing.

    Args:
        message: Telegram message object
        state: FSM context
        user: User object
    """
    # TODO: Implement reminder editing logic
    await message.answer(
        "⏰ Please provide the new reminder time or use /start to cancel."
    )
