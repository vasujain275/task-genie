from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.enums import ContentType

from app.models import User
from app.bot.states import ConversationMode, SettingsFlow
from app.bot.keyboards.inline import get_welcome_keyboard, get_settings_keyboard
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """
    Handles /start command.

    Shows settings webapp if:
    1. User is new (first time using the bot)
    2. User has no Gemini key AND no OpenAI key configured

    Otherwise, shows normal welcome message with quick access to settings.
    """
    try:
        # Clear any existing state when user hits /start
        await state.clear()

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
    except Exception as e:
        logger.error(f"Error in start_handler: {e}", exc_info=True)
        await message.answer("An error occurred. Please try again later.")
        return

    # Check if user needs to configure settings
    # (New user or missing both API keys)
    needs_setup = user.gemini_key is None and user.openai_key is None

    if needs_setup:
        # User needs to configure settings - set state to awaiting configuration
        await state.set_state(SettingsFlow.awaiting_api_key)
        await state.update_data(is_onboarding=True)

        # User needs to configure settings
        await message.answer(
            f"👋 Welcome {user.name}! I'm Task Genie, your personal task and reminder assistant.\n\n"
            "🔧 **First Time Setup Required**\n\n"
            "To get started, I need you to configure your AI provider. I can work with:\n"
            "• 🤖 Google Gemini\n"
            "• 🧠 OpenAI (ChatGPT)\n\n"
            "Click the button below to open settings and add your API key. "
            "Your key will be securely encrypted and stored.\n\n"
            "Once configured, you can tell me tasks in natural language like:\n"
            "• 'Remind me to buy groceries tomorrow at 5pm'\n"
            "• 'Team meeting next Monday at 10am'\n"
            "• 'Call mom this evening'",
            reply_markup=get_welcome_keyboard(),
        )
    else:
        # User is already configured - clear state and set to active mode
        await state.set_state(ConversationMode.active)

        ai_status = (
            "✅"
            if user.default_ai == "gemini"
            else "✅" if user.default_ai == "openai" else "⚠️"
        )

        await message.answer(
            f"👋 Welcome back {user.name}! I'm ready to help you manage tasks.\n\n"
            "Just tell me what you need to do in natural language, like:\n"
            "• 'Remind me to buy groceries tomorrow at 5pm'\n"
            "• 'I need to call mom this evening'\n"
            "• 'Team meeting next Monday at 10am'\n\n"
            f"⚙️ **Current Settings:**\n"
            f"• Timezone: {user.timezone}\n"
            f"• Default AI: {ai_status} {user.default_ai.title()}\n\n"
            "Click the button below to update your settings anytime.",
            reply_markup=get_settings_keyboard(),
        )


@router.message(F.content_type == ContentType.WEB_APP_DATA)
async def webapp_data_handler(message: Message, state: FSMContext):
    """
    Handles data received from Telegram WebApp.
    This is triggered when user submits settings via the webapp.
    """
    logger.info("=== WEBAPP DATA HANDLER TRIGGERED ===")
    try:
        if message.from_user is None or message.web_app_data is None:
            logger.warning("Received webapp data without user info or data")
            return

        logger.info(f"Received webapp data from user {message.from_user.id}")
        logger.debug(f"WebApp data: {message.web_app_data.data}")

        # Parse the data sent from webapp
        import json

        try:
            webapp_data = json.loads(message.web_app_data.data)
            logger.info(f"Parsed webapp data: {webapp_data}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webapp data: {e}")
            await message.answer(
                "❌ Invalid data received from settings. Please try again."
            )
            return

        # Get user from database
        user = await User.find_one(User.telegram_id == message.from_user.id)
        if not user:
            await message.answer("❌ User not found. Please use /start to register.")
            return

        # The webapp data is automatically sent when user closes the webapp
        # Data validation and saving is done on the backend (FastAPI endpoint)
        # Here we just acknowledge and update the user's state

        # Refresh user data to get latest settings
        refreshed_user = await User.find_one(User.telegram_id == message.from_user.id)
        if not refreshed_user:
            await message.answer(
                "❌ Error refreshing user data. Please try /start again."
            )
            return

        # Check if settings are now configured
        settings_configured = (
            refreshed_user.gemini_key is not None
            or refreshed_user.openai_key is not None
        )

        if settings_configured:
            # Get state data to check if this was onboarding
            state_data = await state.get_data()
            is_onboarding = state_data.get("is_onboarding", False)

            if is_onboarding:
                # First time setup completed
                await message.answer(
                    f"✅ **Settings Configured Successfully!**\n\n"
                    f"🎉 You're all set up, {refreshed_user.name}!\n\n"
                    f"⚙️ **Your Settings:**\n"
                    f"• Timezone: {refreshed_user.timezone}\n"
                    f"• AI Provider: {refreshed_user.default_ai.title()}\n\n"
                    f"🚀 **You can now start using me!**\n\n"
                    f"Just send me any task in natural language, like:\n"
                    f"• 'Remind me to buy groceries tomorrow at 5pm'\n"
                    f"• 'Team meeting next Monday at 10am'\n"
                    f"• 'Call mom this evening'\n\n"
                    f"I'll understand and create tasks for you automatically! 🎯"
                )
            else:
                # Settings updated (not first time)
                await message.answer(
                    f"✅ **Settings Updated Successfully!**\n\n"
                    f"⚙️ **Updated Settings:**\n"
                    f"• Timezone: {refreshed_user.timezone}\n"
                    f"• AI Provider: {refreshed_user.default_ai.title()}\n\n"
                    f"You can continue sending me tasks as usual! 📝"
                )

            # Set state to active conversation mode
            await state.set_state(ConversationMode.active)
            await state.update_data(is_onboarding=False)

        else:
            # Settings still not configured
            await message.answer(
                "⚠️ It looks like your settings aren't fully configured yet.\n\n"
                "Please make sure to:\n"
                "• Select an AI provider (Gemini or OpenAI)\n"
                "• Enter a valid API key\n"
                "• Save your settings\n\n"
                "Use /start to try again."
            )
            await state.clear()

    except Exception as e:
        logger.error(f"Error handling webapp data: {e}", exc_info=True)
        await message.answer(
            "❌ An error occurred while processing your settings. "
            "Please try again using /start."
        )
        await state.clear()
