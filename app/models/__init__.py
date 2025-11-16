"""
Models package for Task Genie bot.
Exports all models and provides utility functions for aiogram integration.
"""

from app.models.user import User
from app.models.task import Task
from app.models.reminder import Reminder

# Rebuild models to resolve forward references
Task.model_rebuild()
Reminder.model_rebuild()

__all__ = ["User", "Task", "Reminder"]
