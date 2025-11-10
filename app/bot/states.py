"""
FSM States for conversation flow
"""

from aiogram.fsm.state import State, StatesGroup


class ConversationMode(StatesGroup):
    """Conversation states for task management"""

    active = State()  # User is ready and can send tasks via NLP
    confirming_task = State()  # Waiting for yes/no confirmation on parsed task
    editing_task = State()  # User is editing an existing task


class ReminderFlow(StatesGroup):
    """States for reminder management"""

    awaiting_reminder_input = State()  # Waiting for reminder details
    confirming_reminder = State()  # Confirming reminder creation
    selecting_task = State()  # Selecting task to set reminder for
    editing_reminder = State()  # Editing reminder time


class SettingsFlow(StatesGroup):
    """States for settings configuration"""

    awaiting_timezone = State()  # Waiting for timezone input
    awaiting_api_key = State()  # Waiting for API key input
    selecting_default_ai = State()  # Selecting default AI provider
