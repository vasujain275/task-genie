"""
Settings-related message handlers.
Handles settings configuration via inline keyboards.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from app.models.user import User
from app.bot.states import SetupStates, ConversationMode
from app.bot.keyboards.inline import (
    get_timezone_keyboard,
    get_cancel_keyboard,
    get_settings_keyboard,
)
from app.utils.security import encrypt_api_key
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()


def _is_plausible_api_key(value: str) -> bool:
    key = value.strip()
    return (
        len(key) >= 20
        and any(ch.isalpha() for ch in key)
        and any(ch.isdigit() for ch in key)
    )


@router.message(Command("settings"))
async def settings_command_handler(message: Message, state: FSMContext):
    """Handle /settings command - show current settings and options to change them"""
    if not message.from_user:
        await message.answer("Error: User not found")
        return

    user = await User.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ User not found. Please use /start to register.")
        return

    # Show current settings with options to update
    api_key_status = "✅ Configured" if user.openai_key else "❌ Not configured"

    await message.answer(
        f"⚙️ <b>Your Current Settings</b>\n\n"
        f"👤 <b>User:</b> {user.name}\n"
        f"🌍 <b>Timezone:</b> {user.timezone}\n"
        f"🔑 <b>API Key:</b> {api_key_status}\n\n"
        f"Use the buttons below to update your settings:",
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "setup_timezone")
async def setup_timezone_callback(callback: CallbackQuery, state: FSMContext):
    """Handle timezone setup button click"""
    await callback.answer()

    if not callback.message:
        return

    await callback.message.edit_text(  # type: ignore
        "🌍 <b>Select Your Timezone</b>\n\n"
        "Choose the timezone where you're located. This helps me schedule your tasks and reminders correctly.",
        reply_markup=get_timezone_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("tz_"))
async def timezone_selected_callback(callback: CallbackQuery, state: FSMContext):
    """Handle timezone selection"""
    if not callback.from_user or not callback.message or not callback.data:
        await callback.answer("Error: Invalid callback")
        return

    await callback.answer()

    # Extract timezone from callback data
    timezone = callback.data.replace("tz_", "")

    # Update user's timezone
    user = await User.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.edit_text(
            "❌ User not found. Please use /start to register."
        )  # type: ignore
        return

    user.timezone = timezone
    await user.save()

    logger.info(f"Timezone updated for user {user.telegram_id}: {timezone}")

    # Check if user still needs to setup API key
    if user.openai_key is None:
        await callback.message.edit_text(  # type: ignore
            f"✅ <b>Timezone Set: {timezone}</b>\n\n"
            "🔑 <b>Now, let's set up your API key</b>\n\n"
            "Please send me your API key. You can get one from:\n"
            "https://platform.openai.com/api-keys\n\n"
            "⚠️ <b>Security Note:</b> Your key will be encrypted and stored securely. "
            "The message containing your key will be automatically deleted after storing it.",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(SetupStates.waiting_for_apikey)
    else:
        await callback.message.edit_text(  # type: ignore
            f"✅ <b>Timezone Updated: {timezone}</b>\n\n"
            "Your timezone has been updated successfully!",
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "setup_apikey")
async def setup_apikey_callback(callback: CallbackQuery, state: FSMContext):
    """Handle API key setup button click"""
    await callback.answer()

    if not callback.message:
        return

    await callback.message.edit_text(  # type: ignore
        "🔑 <b>API Key Setup</b>\n\n"
        "Please send me your API key. You can get one from:\n"
        "https://platform.openai.com/api-keys\n\n"
        "⚠️ <b>Security Note:</b> Your key will be encrypted and stored securely. "
        "The message containing your key will be automatically deleted after storing it.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(SetupStates.waiting_for_apikey)


@router.message(SetupStates.waiting_for_apikey)
async def receive_apikey_handler(message: Message, state: FSMContext):
    """Handle OpenAI API key input"""
    if not message.from_user or not message.text:
        await message.answer("Invalid input. Please try again.")
        return

    api_key = message.text.strip()

    if not _is_plausible_api_key(api_key):
        await message.answer(
            "⚠️ That doesn't look like a valid API key. Please check and try again.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    try:
        # Get user and update API key
        user = await User.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ User not found. Please use /start to register.")
            await state.clear()
            return

        # Encrypt and save the API key
        encrypted_key = encrypt_api_key(api_key)
        user.openai_key = encrypted_key
        await user.save()

        try:
            await message.delete()
        except Exception:
            logger.warning(
                f"Could not delete API key message for user {user.telegram_id}"
            )

        logger.info(f"OpenAI API key updated for user {user.telegram_id}")

        # Clear state and set to active mode
        await state.clear()
        await state.set_state(ConversationMode.active)

        # Send success message
        await message.answer(
            f"✅ <b>Setup Complete!</b>\n\n"
            f"🎉 You're all set up, {user.name}!\n\n"
            f"⚙️ <b>Your Settings:</b>\n"
            f"• Timezone: {user.timezone}\n"
            f"• OpenAI: ✅ Configured\n\n"
            f"🚀 <b>You can now start using me!</b>\n\n"
            f"Just send me any task in natural language, like:\n"
            f"• 'Remind me to buy groceries tomorrow at 5pm'\n"
            f"• 'Team meeting next Monday at 10am'\n"
            f"• 'Call mom this evening'\n\n"
            f"I'll understand and create tasks for you automatically! 🎯",
            reply_markup=get_settings_keyboard(),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error saving API key: {e}", exc_info=True)
        await message.answer(
            "❌ An error occurred while saving your API key. Please try again using /start."
        )
        await state.clear()


@router.callback_query(F.data == "cancel_setup")
async def cancel_setup_callback(callback: CallbackQuery, state: FSMContext):
    """Handle cancel button click"""
    await callback.answer()
    await state.clear()

    if not callback.message:
        return

    await callback.message.edit_text(  # type: ignore
        "❌ Setup cancelled.\n\nUse /start anytime to configure your settings."
    )
