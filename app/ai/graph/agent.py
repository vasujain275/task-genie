"""
Custom LangGraph workflow with explicit nodes and edges for task management

========================================
GRAPH ARCHITECTURE
========================================

This is a CUSTOM LangGraph implementation (not using prebuilt agents) for:
- Full control and transparency
- Easy debugging and maintenance
- Simple extensibility

GRAPH FLOW:
    START → agent → [should_continue?] → tools → agent
                         ↓
                        END

COMPONENTS:
1. AgentState: TypedDict holding conversation state
2. agent_node: Calls LLM to decide action (respond or use tools)
3. should_continue: Routes to tools or end based on LLM response
4. tools node: Executes tool calls and returns results

========================================
CONVERSATION MEMORY & CHECKPOINTING
========================================

MEMORY MANAGEMENT:
- Uses LangGraph's built-in MemorySaver for in-memory checkpointing
- Persists conversation history across multiple interactions
- Thread ID format: user_{user_id}_date_{YYYY-MM-DD}
- New thread created daily for each user (resets conversation context)

MESSAGE TRIMMING:
- Maintains last 10 messages per thread (+ system message)
- Automatic trimming after each invocation
- Benefits: token preservation, cost reduction, better performance

THREAD LIFECYCLE:
- Thread persists for the entire day (midnight to midnight)
- Next day = new thread = fresh conversation context
- Old threads remain in memory until app restart

========================================
HOW TO EXTEND
========================================

ADD NEW TOOL:
1. Define tool in app/ai/tools/task_tools.py
2. Add to TASK_TOOLS list
3. That's it! Agent will automatically have access

ADD NEW NODE:
1. Define node function: def my_node(state: AgentState) -> dict
2. Add to workflow: workflow.add_node("my_node", my_node)
3. Add edge: workflow.add_edge("from_node", "my_node")

ADD CONDITIONAL ROUTING:
1. Define router: def my_router(state: AgentState) -> Literal["a", "b"]
2. Use: workflow.add_conditional_edges("node", my_router, {"a": "node_a", "b": "node_b"})

MODIFY STATE:
1. Update AgentState TypedDict
2. Pass new fields when invoking: state = {..., "new_field": value}

========================================
"""

from typing import TypedDict, Annotated, Sequence, Literal
from datetime import datetime
from operator import add

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from pydantic import SecretStr
from zoneinfo import ZoneInfo

from app.ai.tools.task_tools import TASK_TOOLS
from app.ai.prompts.system import AGENT_SYSTEM_PROMPT
from app.utils.logger import setup_logger
from app.config import settings

logger = setup_logger(__name__)

# Global in-memory checkpointer shared across all agent instances
memory_checkpointer = MemorySaver()


# ==================== State Definition ====================


class AgentState(TypedDict):
    """State for the agent graph"""

    messages: Annotated[Sequence[BaseMessage], add]  # Append-only message history
    user_id: int
    user_name: str
    user_timezone: str


# ==================== Helper Functions ====================


def get_thread_id(user_id: int) -> str:
    """
    Generate thread ID based on user_id and current date.
    This creates a new thread for each user every day.

    Format: user_{user_id}_date_{YYYY-MM-DD}
    Example: user_123456789_date_2025-11-16

    Args:
        user_id: Telegram user ID

    Returns:
        Thread ID string
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    thread_id = f"user_{user_id}_date_{current_date}"
    logger.debug(f"Generated thread_id: {thread_id}")
    return thread_id


def trim_message_history(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """
    Trim message history to keep only the last 10 messages.
    Always preserves the system message (first message).

    This helps with:
    - Token preservation
    - Better performance
    - Cost reduction

    Args:
        messages: List of messages in conversation

    Returns:
        Trimmed list of messages with system message preserved
    """
    if len(messages) <= 11:  # System message + 10 conversation messages
        return list(messages)

    # Keep system message (first) + last 10 messages
    system_msg = (
        messages[0] if messages and isinstance(messages[0], SystemMessage) else None
    )

    if system_msg:
        # Trim to last 10 non-system messages
        trimmed = [system_msg] + list(messages[-10:])
        logger.debug(
            f"Trimmed messages from {len(messages)} to {len(trimmed)} (system + last 10)"
        )
        return trimmed
    else:
        # No system message, just keep last 10
        trimmed = list(messages[-10:])
        logger.debug(
            f"Trimmed messages from {len(messages)} to {len(trimmed)} (last 10)"
        )
        return trimmed


def normalize_and_inject_user_id(response: AIMessage, user_id: int) -> None:
    """
    Normalize tool call structure and inject user_id into all tool call arguments.

    This ensures:
    1. All tool calls have a consistent, predictable structure
    2. All tool calls receive the correct Telegram user_id
    3. Invalid structures are caught early with clear error messages

    Args:
        response: AIMessage from LLM (may contain tool_calls)
        user_id: Telegram user ID to inject into tool arguments

    Raises:
        ValueError: If tool call structure is invalid or args is not a dict

    Note:
        Modifies response.tool_calls in-place
    """
    # Early return if no tool calls
    if not hasattr(response, "tool_calls") or not response.tool_calls:
        return

    tool_calls = response.tool_calls  # type: ignore[attr-defined]

    for idx, tc in enumerate(tool_calls):
        # Get tool name for better error messages
        tool_name = "unknown"

        # Normalize: handle both dict and object-like tool calls
        if isinstance(tc, dict):
            tool_name = tc.get("name", "unknown")
            args = tc.get("args")
        else:
            # Object with attributes
            tool_name = getattr(tc, "name", "unknown")
            args = getattr(tc, "args", None)

        # Validate args is a dict
        if not isinstance(args, dict):
            raise ValueError(
                f"Tool call #{idx} ('{tool_name}') has invalid args type: {type(args).__name__}. "
                f"Expected dict, got {type(args)}. This indicates an LLM output format issue."
            )

        # Inject user_id - this is the critical operation
        args["user_id"] = user_id

        logger.debug(
            f"✓ Normalized tool call #{idx}: '{tool_name}' with user_id={user_id}"
        )


# ==================== Node Functions ====================


def agent_node(state: AgentState, llm_with_tools) -> dict:
    """
    Main agent node - calls LLM to decide next action

    The LLM can either:
    1. Respond directly to the user (no tool calls)
    2. Call one or more tools to perform actions

    This node ensures all tool calls are normalized and injected with
    the correct user_id before being passed to the tools node.
    """
    messages = state["messages"]
    user_id = state["user_id"]

    # Call LLM with tools
    response = llm_with_tools.invoke(messages)

    logger.debug(f"Agent response: {response}")

    # Normalize and inject user_id into tool calls
    if isinstance(response, AIMessage):
        try:
            normalize_and_inject_user_id(response, user_id)
        except ValueError as e:
            # Log validation errors and re-raise to fail fast
            logger.error(f"Tool call validation failed: {e}")
            raise

    # Return new message to append to state
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    Routing function - decides whether to call tools or end

    Returns:
        "tools" if the last message has tool calls
        "end" if the agent is done (no tool calls)
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Check if the last message is an AIMessage with tool calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        logger.debug(f"Routing to tools: {len(last_message.tool_calls)} tool call(s)")
        return "tools"

    # Otherwise, end the conversation turn
    logger.debug("Routing to end - no tool calls")
    return "end"


# ==================== Graph Builder ====================


def create_task_agent(
    openai_key: str, user_id: int, user_name: str, user_timezone: str
):
    """
    Create a custom LangGraph agent with explicit nodes and edges.

    Graph structure:
        START -> agent -> [should_continue] -> tools -> agent
                              |
                              └─> END

    Args:
        openai_key: OpenAI API key
        user_id: Telegram user ID
        user_name: User's name
        user_timezone: User's timezone

    Returns:
        Compiled agent graph
    """

    # ========== Setup LLM with tools ==========
    llm = ChatOpenAI(
        model=settings.LLM,  # type: ignore[call-arg]
        api_key=SecretStr(openai_key),  # type: ignore[call-arg]
        temperature=0.7,  # type: ignore[call-arg]
    )

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(TASK_TOOLS)

    # ========== Format system prompt ==========
    tz = ZoneInfo(user_timezone)
    current_datetime = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

    system_message = SystemMessage(
        content=AGENT_SYSTEM_PROMPT.format(
            current_datetime=current_datetime,
            user_name=user_name,
            user_timezone=user_timezone,
        )
    )

    # ========== Build the graph ==========
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", lambda state: agent_node(state, llm_with_tools))  # type: ignore[arg-type]
    workflow.add_node("tools", ToolNode(TASK_TOOLS))

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", "end": END}
    )

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Compile the graph with memory checkpointer
    graph = workflow.compile(checkpointer=memory_checkpointer)

    logger.info(
        f"✅ Custom task agent graph created for user {user_id} with in-memory checkpointing"
    )

    # Return a wrapper that injects system message and handles invocation
    class AgentWrapper:
        """Wrapper to handle system message injection and provide clean API"""

        def __init__(self, graph, system_msg, user_id, user_name, user_timezone):
            self.graph = graph
            self.system_msg = system_msg
            self.user_id = user_id
            self.user_name = user_name
            self.user_timezone = user_timezone

        def invoke(self, input_dict, config=None):
            """Synchronous invoke - prepends system message and uses checkpointing"""
            messages = input_dict.get("messages", [])

            # Prepend system message if not already present
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [self.system_msg] + list(messages)

            # Build complete state
            state = {
                "messages": messages,
                "user_id": self.user_id,
                "user_name": self.user_name,
                "user_timezone": self.user_timezone,
            }

            # Generate thread_id for checkpointing
            thread_id = get_thread_id(self.user_id)

            # Build config with thread_id
            if config is None:
                config = {}
            config["configurable"] = {"thread_id": thread_id}

            logger.debug(f"Invoking graph with thread_id: {thread_id}")

            # Invoke graph with checkpointing
            result = self.graph.invoke(state, config)

            # Trim message history after invocation to keep only last 10 messages
            if isinstance(result, dict) and "messages" in result:
                result["messages"] = trim_message_history(result["messages"])

            return result

        async def ainvoke(self, input_dict, config=None):
            """Async invoke - prepends system message and uses checkpointing"""
            messages = input_dict.get("messages", [])

            # Prepend system message if not already present
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [self.system_msg] + list(messages)

            # Build complete state
            state = {
                "messages": messages,
                "user_id": self.user_id,
                "user_name": self.user_name,
                "user_timezone": self.user_timezone,
            }

            # Generate thread_id for checkpointing
            thread_id = get_thread_id(self.user_id)

            # Build config with thread_id
            if config is None:
                config = {}
            config["configurable"] = {"thread_id": thread_id}

            logger.debug(f"Invoking graph with thread_id: {thread_id}")

            # Invoke graph with checkpointing
            result = await self.graph.ainvoke(state, config)

            # Trim message history after invocation to keep only last 10 messages
            if isinstance(result, dict) and "messages" in result:
                result["messages"] = trim_message_history(result["messages"])

            return result

    return AgentWrapper(graph, system_message, user_id, user_name, user_timezone)
