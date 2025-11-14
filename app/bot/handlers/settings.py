"""
Settings-related message handlers.
Handles settings configuration via inline keyboards.
"""

from typing import cast
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
        f"⚙️ **Your Current Settings**\n\n"
        f"👤 **User:** {user.name}\n"
        f"🌍 **Timezone:** {user.timezone}\n"
        f"🔑 **OpenAI Key:** {api_key_status}\n\n"
        f"Use the buttons below to update your settings:",
        reply_markup=get_settings_keyboard(),
    )



@router.callback_query(F.data == "setup_timezone")
async def setup_timezone_callback(callback: CallbackQuery, state: FSMContext):
    """Handle timezone setup button click"""
    await callback.answer()

    if not callback.message:
        return

    await callback.message.edit_text(  # type: ignore
        "🌍 **Select Your Timezone**\n\n"
        "Choose the timezone where you're located. This helps me schedule your tasks and reminders correctly.",
        reply_markup=get_timezone_keyboard(),
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
        await callback.message.edit_text("❌ User not found. Please use /start to register.")  # type: ignore
        return

    user.timezone = timezone
    await user.save()

    logger.info(f"Timezone updated for user {user.telegram_id}: {timezone}")

    # Check if user still needs to setup API key
    if user.openai_key is None:
        await callback.message.edit_text(  # type: ignore
            f"✅ **Timezone Set: {timezone}**\n\n"
            "🔑 **Now, let's set up your OpenAI API key**\n\n"
            "Please send me your OpenAI API key. You can get one from:\n"
            "https://platform.openai.com/api-keys\n\n"
            "⚠️ **Security Note:** Your key will be encrypted and stored securely. "
            "The message containing your key will be automatically deleted after storing it.",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(SetupStates.waiting_for_apikey)
    else:
        await callback.message.edit_text(  # type: ignore
            f"✅ **Timezone Updated: {timezone}**\n\n"
            "Your timezone has been updated successfully!",
            reply_markup=get_settings_keyboard(),
        )


@router.callback_query(F.data == "setup_apikey")
async def setup_apikey_callback(callback: CallbackQuery, state: FSMContext):
    """Handle API key setup button click"""
    await callback.answer()

    if not callback.message:
        return

    await callback.message.edit_text(  # type: ignore
        "🔑 **OpenAI API Key Setup**\n\n"
        "Please send me your OpenAI API key. You can get one from:\n"
        "https://platform.openai.com/api-keys\n\n"
        "⚠️ **Security Note:** Your key will be encrypted and stored securely. "
        "The message containing your key will be automatically deleted after storing it.",
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(SetupStates.waiting_for_apikey)


@router.message(SetupStates.waiting_for_apikey)
async def receive_apikey_handler(message: Message, state: FSMContext):
    """Handle OpenAI API key input"""
    if not message.from_user or not message.text:
        await message.answer("Invalid input. Please try again.")
        return

    api_key = message.text.strip()

    # Basic validation - OpenAI keys start with 'sk-'
    if not api_key.startswith("sk-"):
        await message.answer(
            "⚠️ That doesn't look like a valid OpenAI API key.\n\n"
            "OpenAI API keys start with 'sk-'. Please check and try again.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    try:
        # Delete the message containing the API key for security
        await message.delete()

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

        logger.info(f"OpenAI API key updated for user {user.telegram_id}")

        # Clear state and set to active mode
        await state.clear()
        await state.set_state(ConversationMode.active)

        # Send success message
        await message.answer(
            f"✅ **Setup Complete!**\n\n"
            f"🎉 You're all set up, {user.name}!\n\n"
            f"⚙️ **Your Settings:**\n"
            f"• Timezone: {user.timezone}\n"
            f"• OpenAI: ✅ Configured\n\n"
            f"🚀 **You can now start using me!**\n\n"
            f"Just send me any task in natural language, like:\n"
            f"• 'Remind me to buy groceries tomorrow at 5pm'\n"
            f"• 'Team meeting next Monday at 10am'\n"
            f"• 'Call mom this evening'\n\n"
            f"I'll understand and create tasks for you automatically! 🎯",
            reply_markup=get_settings_keyboard(),
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
        "❌ Setup cancelled.\n\n"
        "Use /start anytime to configure your settings."
    )
