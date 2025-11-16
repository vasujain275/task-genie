"""
FSM States for conversation flow
"""

from aiogram.fsm.state import State, StatesGroup


class SetupStates(StatesGroup):
    """States for initial setup and configuration"""

    waiting_for_apikey = State()  # Waiting for user to send OpenAI API key


class ConversationMode(StatesGroup):
    """Simplified conversation states"""

    active = State()  # User is in conversation mode - AI handles all interactions


class TaskCreationStates(StatesGroup):
    """States for natural language task creation flow"""

    waiting_for_nl_input = State()  # Waiting for natural language task description
    confirming_task = State()  # Asking user to confirm parsed task details
    editing_task_details = State()  # User wants to modify task details
    processing = State()  # Processing and saving the task
