"""
Natural language conversation handler using ReAct agent
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from langchain_core.messages import HumanMessage

from app.models.user import User
from app.bot.states import ConversationMode
from app.ai.graph.agent import create_task_agent
from app.utils.logger import setup_logger
from app.utils.security import decrypt_api_key

logger = setup_logger(__name__)
router = Router()


@router.message(
    StateFilter(ConversationMode.active),
    F.text & ~F.text.startswith("/")
)
async def handle_conversation(message: Message, state: FSMContext):
    """
    Handle natural language messages when in active conversation mode.

    This uses a ReAct agent that can:
    - Have natural conversations
    - Create/edit/delete tasks
    - Set reminders
    - List tasks and provide statistics
    - And more!
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
                "Use /settings to configure your API key.",
            )
            return

        if not message.text:
            await message.answer("Please send a text message.")
            return

        logger.info(f"Processing message from user {user.telegram_id}: {message.text}")

        # Show typing indicator
        await message.bot.send_chat_action(message.chat.id, "typing")  # type: ignore[union-attr]

        # Decrypt API key
        openai_key = decrypt_api_key(user.openai_key)  # type: ignore[arg-type]

        # Create agent for this user
        agent = create_task_agent(
            openai_key=openai_key,  # type: ignore[arg-type]
            user_id=user.telegram_id,
            user_name=user.name,
            user_timezone=user.timezone
        )

        # Invoke agent with user message
        response = await agent.ainvoke({
            "messages": [HumanMessage(content=message.text)]
        })

        # Extract the last message from the agent
        if response and "messages" in response:
            last_message = response["messages"][-1]
            agent_response = last_message.content  # type: ignore[union-attr]
        else:
            agent_response = "I couldn't process that. Could you try again?"

        # Send response - try Markdown first, fall back to plain text if it fails
        try:
            await message.answer(agent_response, parse_mode="Markdown")
        except Exception as markdown_error:
            logger.warning(f"Markdown parsing failed, sending as plain text: {markdown_error}")
            # Send without markdown parsing
            await message.answer(agent_response)

    except Exception as e:
        logger.error(f"Error in handle_conversation: {e}", exc_info=True)
        await message.answer("Sorry, something went wrong. Please try again.")
