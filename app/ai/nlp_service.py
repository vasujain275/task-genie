"""
NLP Service - Main interface for natural language task processing
"""

from typing import Optional, Dict, Any
from datetime import datetime, date

from app.ai.graph.task_flow import build_task_creation_graph
from app.ai.checkpointer import get_checkpointer, get_conversation_id
from app.ai.state import GraphState
from app.models.user import User
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class NLPService:
    """
    Main service for processing natural language inputs and managing task creation.

    This service:
    1. Manages conversation state with daily isolation (userId + date)
    2. Coordinates LangGraph workflow for task parsing
    3. Handles confirmation flow
    4. Maintains conversation context
    """

    def __init__(self):
        self.graph = None
        self.checkpointer = None

    async def initialize(self):
        """Initialize the service with graph and checkpointer"""
        if self.graph is None:
            # Get checkpointer
            self.checkpointer = await get_checkpointer()

            # Build and compile graph with checkpointer
            workflow = build_task_creation_graph()
            self.graph = workflow.compile(checkpointer=self.checkpointer)

            logger.info("NLP Service initialized with graph and checkpointer")

    async def process_message(
        self,
        user_id: int,
        user_message: str,
        user_name: str,
        user_timezone: str = "UTC",
        conversation_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language message from the user.

        Args:
            user_id: Telegram user ID
            user_message: User's message text
            user_name: User's name
            user_timezone: User's timezone
            conversation_date: Date for conversation (defaults to today)

        Returns:
            Dictionary with:
                - response_message: Message to send back to user
                - needs_confirmation: Whether waiting for user confirmation
                - confirmation_message: Message asking for confirmation (if needs_confirmation)
                - task_created: Whether task was successfully created
                - error: Error message if any
        """
        await self.initialize()

        try:
            # Generate conversation ID (userId + date)
            thread_id = get_conversation_id(user_id, conversation_date)

            logger.info(f"Processing message for thread: {thread_id}")

            # Create initial state
            initial_state: GraphState = {
                "user_message": user_message,
                "user_id": user_id,
                "user_name": user_name,
                "user_timezone": user_timezone,
                "messages": [],
                "conversation_id": thread_id,
                "task_data": None,
                "reminder_data": None,
                "has_reminder": False,
                "needs_confirmation": False,
                "user_confirmed": None,
                "confirmation_message": "",
                "error": None,
                "retry_count": 0,
                "task_created": False,
                "reminder_created": False,
                "response_message": ""
            }

            # Configure with thread_id for checkpointing
            config = {
                "configurable": {
                    "thread_id": thread_id
                }
            }

            # Run the graph (will stop at confirmation point)
            result = await self.graph.ainvoke(initial_state, config)  # type: ignore[union-attr,arg-type]

            # Return result
            return {
                "response_message": result.get("response_message", ""),
                "needs_confirmation": result.get("needs_confirmation", False),
                "confirmation_message": result.get("confirmation_message", ""),
                "task_created": result.get("task_created", False),
                "reminder_created": result.get("reminder_created", False),
                "error": result.get("error"),
                "task_data": result.get("task_data"),
                "reminder_data": result.get("reminder_data")
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "response_message": "An error occurred while processing your request. Please try again.",
                "needs_confirmation": False,
                "confirmation_message": "",
                "task_created": False,
                "error": str(e)
            }

    async def confirm_task(
        self,
        user_id: int,
        conversation_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Confirm and create the task that was previously parsed.

        Args:
            user_id: Telegram user ID
            conversation_date: Date for conversation (defaults to today)

        Returns:
            Dictionary with task creation result
        """
        await self.initialize()

        try:
            # Generate conversation ID
            thread_id = get_conversation_id(user_id, conversation_date)

            logger.info(f"Confirming task for thread: {thread_id}")

            # Configure with thread_id
            config = {
                "configurable": {
                    "thread_id": thread_id
                }
            }

            # Get current state from checkpoint using async method
            checkpoint_tuple = await self.checkpointer.aget_tuple(config)  # type: ignore[union-attr]

            if not checkpoint_tuple or not checkpoint_tuple.checkpoint.get("channel_values"):
                return {
                    "response_message": "No pending task to confirm. Please tell me what task you'd like to create.",
                    "needs_confirmation": False,
                    "task_created": False,
                    "error": "No pending task"
                }

            # Get the actual state from checkpoint
            current_state = checkpoint_tuple.checkpoint["channel_values"]

            if not current_state.get("task_data"):
                return {
                    "response_message": "No pending task to confirm. Please tell me what task you'd like to create.",
                    "needs_confirmation": False,
                    "task_created": False,
                    "error": "No pending task"
                }

            # Update state with confirmation and invoke create_task directly
            confirmed_state: GraphState = {
                **current_state,  # type: ignore[arg-type]
                "user_confirmed": True
            }

            # Call create_task node directly
            from app.ai.graph.task_flow import create_task_node
            result = await create_task_node(confirmed_state)

            return {
                "response_message": result.get("response_message", "✅ Task created successfully!"),
                "needs_confirmation": False,
                "task_created": result.get("task_created", False),
                "reminder_created": result.get("reminder_created", False),
                "error": result.get("error")
            }

        except Exception as e:
            logger.error(f"Error confirming task: {e}", exc_info=True)
            return {
                "response_message": "Failed to create task. Please try again.",
                "needs_confirmation": False,
                "task_created": False,
                "error": str(e)
            }


# Global service instance
_nlp_service: Optional[NLPService] = None


async def get_nlp_service() -> NLPService:
    """
    Get or create the global NLP service instance.

    Returns:
        NLPService instance
    """
    global _nlp_service
    if _nlp_service is None:
        _nlp_service = NLPService()
        await _nlp_service.initialize()
    return _nlp_service
