"""
Inline keyboard builders
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for first time setup"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌍 Select Timezone",
                    callback_data="setup_timezone"
                )
            ]
        ]
    )


def get_timezone_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with common timezone options"""
    timezones = [
        ("🇺🇸 US Eastern", "America/New_York"),
        ("🇺🇸 US Pacific", "America/Los_Angeles"),
        ("🇬🇧 UK/UTC", "Europe/London"),
        ("🇪🇺 Central Europe", "Europe/Paris"),
        ("🇮🇳 India", "Asia/Kolkata"),
        ("🇯🇵 Japan", "Asia/Tokyo"),
        ("🇦🇺 Australia (Sydney)", "Australia/Sydney"),
        ("🌍 UTC", "UTC"),
    ]

    keyboard = []
    for label, tz_data in timezones:
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"tz_{tz_data}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for accessing settings"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚙️ Change Timezone",
                    callback_data="setup_timezone"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔑 Update OpenAI Key",
                    callback_data="setup_apikey"
                )
            ]
        ]
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with cancel button"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_setup"
                )
            ]
        ]
    )


def get_task_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for task confirmation with Yes/No buttons"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Yes, create it",
                    callback_data="confirm_task"
                ),
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data="cancel_task"
                )
            ]
        ]
    )

