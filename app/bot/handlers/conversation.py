"""Natural language conversation handler."""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from app.application.services.conversation import ConversationService
from app.bot.adapters.conversation import (
    build_request_context,
    present_application_result,
)
from app.bot.states import ConversationMode
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()
conversation_service = ConversationService()


@router.message(StateFilter(ConversationMode.active), F.text & ~F.text.startswith("/"))
async def handle_conversation(message: Message, state: FSMContext):
    try:
        if not message.from_user:
            await message.answer("User information not available.")
            return

        if not message.text:
            await message.answer("Please send a text message.")
            return

        await message.bot.send_chat_action(message.chat.id, "typing")  # type: ignore[union-attr]
        context = build_request_context(message)
        result = await conversation_service.handle_message(context, message.text)
        await present_application_result(message, result)

    except Exception as e:
        logger.error(f"Error in handle_conversation: {e}", exc_info=True)
        await message.answer("Sorry, something went wrong. Please try again.")
