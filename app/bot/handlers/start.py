from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.models import User
from app.bot.states import ConversationMode
from app.bot.keyboards.inline import get_welcome_keyboard, get_settings_keyboard
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """
    Handles /start command.

    Shows setup flow if:
    1. User is new (first time using the bot)
    2. User has no OpenAI key configured

    Otherwise, shows normal welcome message with quick access to settings.
    """
    try:
        # Get or create user
        user = None
        if message.from_user:
            logger.info(f"Processing /start command from user: {message.from_user.id}")
            user = await User.get_or_create(
                message.from_user.id,
                message.from_user.first_name,
                message.from_user.username,
            )
            logger.debug(f"User retrieved/created: {user.telegram_id}")
        else:
            logger.warning("Received /start command without user information")
            await message.answer("Unable to retrieve user ID")
            return

        # Clear any existing state after a successful user lookup
        await state.clear()
    except Exception as e:
        logger.error(f"Error in start_handler: {e}", exc_info=True)
        await message.answer("An error occurred. Please try again later.")
        return

    # Check if user needs to configure settings
    needs_setup = user.openai_key is None

    if needs_setup:
        # User needs to configure settings
        await message.answer(
            f"👋 Welcome {user.name}! I'm Task Genie, your personal task and reminder assistant.\n\n"
            "🔧 **First Time Setup Required**\n\n"
            "To get started, I need you to configure:\n"
            "1. 🌍 Your timezone\n"
            "2. 🔑 Your OpenAI API key\n\n"
            "Your API key will be securely encrypted and stored.\n\n"
            "Once configured, you can tell me tasks in natural language like:\n"
            "• 'Remind me to buy groceries tomorrow at 5pm'\n"
            "• 'Team meeting next Monday at 10am'\n"
            "• 'Call mom this evening'\n\n"
            "Let's get started! 🚀",
            reply_markup=get_welcome_keyboard(),
        )
    else:
        # User is already configured - set to active mode
        await state.set_state(ConversationMode.active)

        await message.answer(
            f"👋 Welcome back {user.name}! I'm ready to help you manage tasks.\n\n"
            "Just tell me what you need to do in natural language, like:\n"
            "• 'Remind me to buy groceries tomorrow at 5pm'\n"
            "• 'I need to call mom this evening'\n"
            "• 'Team meeting next Monday at 10am'\n\n"
            f"⚙️ **Current Settings:**\n"
            f"• Timezone: {user.timezone}\n"
            f"• OpenAI: ✅ Configured\n\n"
            "Use the button below to update your settings anytime.",
            reply_markup=get_settings_keyboard(),
        )
