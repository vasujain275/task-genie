"""
FSM States for conversation flow
"""

from aiogram.fsm.state import State, StatesGroup


class SetupStates(StatesGroup):
    """States for initial setup and configuration"""

    waiting_for_apikey = State()  # Waiting for user to send OpenAI API key


class ConversationMode(StatesGroup):
    """Simplified conversation states - AI agent handles everything"""

    active = State()  # User is in conversation mode - AI agent with tools handles all interactions
