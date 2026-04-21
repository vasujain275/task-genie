"""
Models package for Task Genie bot.
Exports all models and provides utility functions for aiogram integration.
"""

from app.models.user import User
from app.models.task import Task
from app.models.reminder import Reminder
from app.models.conversation_turn import ConversationTurn
import app.models.conversation_turn as conversation_turn

# Rebuild models to resolve forward references after all models are imported
# This is necessary because Task has Link["User"] and Reminder has Link["Task"]
User.model_rebuild()
Task.model_rebuild()
Reminder.model_rebuild()
ConversationTurn.model_rebuild()

__all__ = ["User", "Task", "Reminder", "ConversationTurn", "conversation_turn"]
