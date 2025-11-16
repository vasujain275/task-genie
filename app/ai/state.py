"""
State management for LangGraph conversation flow
"""

from typing import TypedDict, Optional, List, Literal
from datetime import datetime


class TaskData(TypedDict, total=False):
    """Parsed task information"""
    title: str
    description: Optional[str]
    task_datetime: datetime
    priority: Literal["low", "medium", "high"]
    tags: List[str]
    recurrence: Optional[str]


class ReminderData(TypedDict, total=False):
    """Parsed reminder information"""
    remind_at: datetime
    message: Optional[str]
    recurrence: Optional[str]


class GraphState(TypedDict):
    """
    State for the task parsing conversation graph.

    This state is passed between all nodes in the LangGraph workflow.
    """
    # User input
    user_message: str
    user_id: int
    user_name: str
    user_timezone: str

    # Conversation context
    messages: List[dict]  # Chat history for context
    conversation_id: str  # userId + date for daily conversations

    # Parsed data
    task_data: Optional[TaskData]
    reminder_data: Optional[ReminderData]
    has_reminder: bool

    # Workflow control
    needs_confirmation: bool
    user_confirmed: Optional[bool]
    confirmation_message: str  # The message to show user for confirmation

    # Error handling
    error: Optional[str]
    retry_count: int

    # Final result
    task_created: bool
    reminder_created: bool
    response_message: str
