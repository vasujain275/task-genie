"""
Inline keyboard builders
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import settings


def get_welcome_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for first time users or users missing API keys"""
    webapp_url = settings.TELEGRAM_WEBAPP_URL

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚙️ Configure Settings",
                    web_app=WebAppInfo(url=f"{webapp_url}/settings"),
                )
            ]
        ]
    )


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with settings button for quick access"""
    webapp_url = settings.TELEGRAM_WEBAPP_URL

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚙️ Settings", web_app=WebAppInfo(url=f"{webapp_url}/settings")
                )
            ]
        ]
    )
