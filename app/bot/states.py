"""
FSM States for conversation flow
"""

from aiogram.fsm.state import State, StatesGroup


class ConversationMode(StatesGroup):
    """Conversation states for task management"""
    active = State()              # User can send tasks
    confirming_task = State()     # Waiting for yes/no confirmation
