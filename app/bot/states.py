"""
FSM States for conversation flow
"""

from aiogram.fsm.state import State, StatesGroup


class ConversationMode(StatesGroup):
    """Simplified conversation states"""

    active = State()  # User is in conversation mode - AI handles all interactions


class SettingsFlow(StatesGroup):
    """States for settings configuration"""

    awaiting_timezone = State()  # Waiting for timezone input
    awaiting_api_key = State()  # Waiting for API key input
    selecting_default_ai = State()  # Selecting default AI provider
