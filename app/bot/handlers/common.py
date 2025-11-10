"""
Common message handler - Simplified natural language message processor.
Uses LangGraph AI agent to handle all task and reminder interactions.
"""

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from app.models.user import User
from app.bot.states import ConversationMode, SettingsFlow
from app.bot.handlers.settings import (
    handle_timezone_setting,
    handle_api_key_setting,
    handle_ai_provider_selection,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()


async def process_natural_language(message: types.Message, state: FSMContext, user: User):
    """
    Process natural language input using LangGraph AI agent.

    This function will delegate to a LangGraph agent that handles:
    - Understanding user intent (task creation, reminder setting, updates, queries)
    - Extracting relevant entities (dates, times, priorities, etc.)
    - Managing conversation context and follow-ups
    - Creating/updating tasks and reminders in MongoDB
    - Handling multi-turn conversations like "remind me 30 min earlier"

    Examples of what the AI will handle:
    - "I have to call mom today evening" -> Creates task + sets reminder 15 min before
    - "No, remind me 30 min earlier" -> Updates reminder time
    - "Remind me 1hr before too" -> Adds additional reminder
    - "Change the deadline to tomorrow" -> Updates task due date
    - "Show me my tasks for today" -> Queries and displays tasks

    Args:
        message: Telegram message object
        state: FSM context for maintaining conversation history
        user: User object
    """
    if message.text is None:
        return

    logger.info(f"Processing natural language from user {user.telegram_id}: {message.text}")

    try:
        # TODO: Implement LangGraph agent integration
        # The agent should:
        # 1. Maintain conversation context from FSM state
        # 2. Process the user message with intent classification
        # 3. Extract entities (task details, reminder times, etc.)
        # 4. Perform database operations (create/update tasks/reminders)
        # 5. Generate natural language responses
        # 6. Update conversation state for follow-up interactions
        #
        # Example implementation structure:
        # ---------------------------------
        # from app.services.langgraph_service import LangGraphService
        #
        # langgraph_service = LangGraphService()
        #
        # # Get conversation history from state
        # data = await state.get_data()
        # conversation_history = data.get("conversation_history", [])
        #
        # # Process with LangGraph agent
        # response = await langgraph_service.process_message(
        #     user=user,
        #     message=message.text,
        #     conversation_history=conversation_history
        # )
        #
        # # Update conversation history
        # conversation_history.append({
        #     "user": message.text,
        #     "assistant": response["text"],
        #     "timestamp": datetime.now()
        # })
        # await state.update_data(conversation_history=conversation_history)
        #
        # # Send response to user
        # await message.answer(response["text"])

        # Temporary placeholder response
        await message.answer(
            "🤖 LangGraph AI integration coming soon!\n\n"
            f"I received: \"{message.text}\"\n\n"
            "Soon I'll be able to:\n"
            "• Create tasks from natural language\n"
            "• Set reminders automatically (15 min before by default)\n"
            "• Handle follow-ups like 'remind me earlier'\n"
            "• Update tasks and reminders conversationally\n"
            "• Remember context from our conversation"
        )

    except Exception as e:
        logger.error(f"Error processing natural language: {e}", exc_info=True)
        await message.answer(
            "⚠️ Sorry, I encountered an error processing your message. Please try again."
        )


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
        # Settings-related states
        if current_state == SettingsFlow.awaiting_timezone:
            await handle_timezone_setting(message, state, user)

        elif current_state == SettingsFlow.awaiting_api_key:
            await handle_api_key_setting(message, state, user)

        elif current_state == SettingsFlow.selecting_default_ai:
            await handle_ai_provider_selection(message, state, user)

        # Active conversation mode - Let LangGraph AI handle everything
        elif current_state == ConversationMode.active or current_state is None:
            await process_natural_language(message, state, user)

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
