"""
LangGraph workflow for task creation from natural language
"""

from typing import Dict, Any, Literal, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

from app.ai.state import GraphState, TaskData, ReminderData
from app.ai.tools.parser import (
    parse_task_from_nl,
    generate_confirmation_message
)
from app.models.task import Task
from app.models.reminder import Reminder
from app.models.user import User
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def parse_input_node(state: GraphState) -> GraphState:
    """
    Parse natural language input to extract task and reminder information.

    This is the first node in the graph - it takes user input and uses AI
    to extract structured task data.
    """
    logger.info(f"Parsing NL input for user {state['user_id']}: {state['user_message']}")

    try:
        # Get user from database to get OpenAI key
        user = await User.get_by_telegram_id(state['user_id'])
        if not user or not user.openai_key:
            return {
                **state,
                "error": "OpenAI API key not configured. Please use /settings to set it up.",
                "needs_confirmation": False,
                "response_message": "⚠️ Please configure your OpenAI API key in settings first."
            }

        # Decrypt API key
        from app.utils.security import decrypt_api_key
        openai_key = decrypt_api_key(user.openai_key)  # type: ignore[arg-type]

        # Parse task from natural language
        parsed_data = await parse_task_from_nl(
            state['user_message'],
            state['user_timezone'],
            openai_key  # type: ignore[arg-type]
        )        # Check for parsing errors
        if "error" in parsed_data or not parsed_data.get("task_title"):
            return {
                **state,
                "error": parsed_data.get("error", "Could not understand the task"),
                "needs_confirmation": False,
                "response_message": "I couldn't understand that task. Could you rephrase it?\n\n"
                                   "For example: 'Call mom tomorrow at 6pm' or 'Team meeting next Monday at 10am'"
            }

        # Create task data structure
        task_data: TaskData = {
            "title": parsed_data["task_title"],
            "description": parsed_data.get("task_description"),
            "task_datetime": parsed_data["task_datetime"],
            "priority": parsed_data.get("priority", "medium"),
            "tags": parsed_data.get("tags", []),
            "recurrence": parsed_data.get("recurrence")
        }

        # Create reminder data structure
        has_reminder = bool(parsed_data.get("reminder_time"))
        reminder_data: Optional[ReminderData] = {
            "remind_at": parsed_data["reminder_time"],
            "message": None,
            "recurrence": parsed_data.get("recurrence")
        } if has_reminder else None

        # Generate confirmation message
        confirmation_msg = generate_confirmation_message(
            task_data["title"],  # type: ignore[typeddict-item]
            task_data["task_datetime"],  # type: ignore[typeddict-item]
            reminder_data["remind_at"] if reminder_data else task_data["task_datetime"],  # type: ignore[typeddict-item,index]
            state['user_timezone'],
            task_data.get("description")  # type: ignore[typeddict-item]
        )

        return {
            **state,
            "task_data": task_data,
            "reminder_data": reminder_data,
            "has_reminder": has_reminder,
            "needs_confirmation": True,
            "confirmation_message": confirmation_msg,
            "error": None
        }

    except Exception as e:
        logger.error(f"Error in parse_input_node: {e}", exc_info=True)
        return {
            **state,
            "error": str(e),
            "needs_confirmation": False,
            "response_message": "An error occurred while parsing your task. Please try again."
        }


async def create_task_node(state: GraphState) -> GraphState:
    """
    Create the task and reminder in the database.

    This node is called after user confirmation.
    """
    task_data = state.get('task_data')
    if not task_data:
        return {
            **state,
            "error": "No task data available",
            "task_created": False
        }

    logger.info(f"Creating task for user {state['user_id']}: {task_data.get('title', 'Unknown')}")

    try:
        # Get user
        user = await User.get_by_telegram_id(state['user_id'])
        if not user:
            return {
                **state,
                "error": "User not found",
                "task_created": False,
                "response_message": "Error: User not found. Please try /start again."
            }

        # Create task
        task = Task(
            user=user,  # type: ignore[arg-type]
            title=task_data['title'],  # type: ignore[typeddict-item]
            description=task_data.get('description'),  # type: ignore[typeddict-item]
            task_datetime=task_data['task_datetime'],  # type: ignore[typeddict-item]
            priority=task_data.get('priority', 'medium'),  # type: ignore[typeddict-item,arg-type]
            tags=task_data.get('tags', []),  # type: ignore[typeddict-item]
            recurrence=task_data.get('recurrence'),  # type: ignore[typeddict-item]
            status='pending'
        )
        await task.insert()
        logger.info(f"Task created with ID: {task.id}")

        # Create reminder if present
        reminder_created = False
        reminder_data = state.get('reminder_data')
        if state['has_reminder'] and reminder_data:
            reminder = Reminder(
                task=task,  # type: ignore[arg-type]
                user=user,  # type: ignore[arg-type]
                remind_at=reminder_data['remind_at'],  # type: ignore[typeddict-item,index]
                message=reminder_data.get('message'),  # type: ignore[typeddict-item]
                recurrence=reminder_data.get('recurrence'),  # type: ignore[typeddict-item]
                sent=False
            )
            await reminder.insert()
            reminder_created = True
            logger.info(f"Reminder created with ID: {reminder.id}")

        # Generate success message
        from app.ai.tools.parser import format_datetime_human_readable

        task_time = format_datetime_human_readable(
            task.task_datetime,
            state['user_timezone']
        )

        response = f"✅ Task created successfully!\n\n"
        response += f"📋 **{task.title}**\n"
        response += f"📅 Due: {task_time}\n"

        if task.description:
            response += f"📝 {task.description}\n"

        if reminder_created and reminder_data:
            reminder_time = format_datetime_human_readable(
                reminder_data['remind_at'],  # type: ignore[typeddict-item,index]
                state['user_timezone']
            )
            response += f"\n🔔 Reminder set for {reminder_time}"

        return {
            **state,
            "task_created": True,
            "reminder_created": reminder_created,
            "response_message": response,
            "error": None
        }

    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        return {
            **state,
            "task_created": False,
            "reminder_created": False,
            "error": str(e),
            "response_message": "❌ Failed to create task. Please try again."
        }


def should_confirm(state: GraphState) -> Literal["confirm", "error"]:
    """
    Determine if we need confirmation or if there was an error.
    """
    if state.get("error"):
        return "error"
    if state.get("needs_confirmation"):
        return "confirm"
    return "error"


def build_task_creation_graph() -> StateGraph:
    """
    Build the task creation workflow graph.

    Flow:
    1. Parse natural language input -> extract task/reminder
    2. If successful, ask for confirmation
    3. On confirmation, create task and reminder in DB
    4. Return success message
    """
    # Create graph
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("parse_input", parse_input_node)
    workflow.add_node("create_task", create_task_node)

    # Set entry point
    workflow.set_entry_point("parse_input")

    # Add conditional edges from parse_input
    workflow.add_conditional_edges(
        "parse_input",
        should_confirm,
        {
            "confirm": "create_task",  # Will be handled by handler before calling create_task
            "error": END
        }
    )

    # Add edge from create_task to end
    workflow.add_edge("create_task", END)

    return workflow


# Compile the graph (will be done with checkpointer in nlp_service)
task_creation_graph = build_task_creation_graph()
