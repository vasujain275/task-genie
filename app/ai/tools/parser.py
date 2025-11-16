"""
Tools for task parsing and natural language processing
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import dateparser  # type: ignore[import-untyped]
from zoneinfo import ZoneInfo

from app.ai.prompts.system import TASK_PARSER_SYSTEM_PROMPT
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def parse_datetime_with_context(
    text: str,
    timezone: str = "UTC",
    reference_datetime: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Parse datetime from natural language text with timezone awareness.

    Args:
        text: Natural language text containing date/time
        timezone: User's timezone
        reference_datetime: Reference datetime for relative parsing

    Returns:
        Parsed datetime or None
    """
    try:
        tz = ZoneInfo(timezone)

        # Use reference datetime or current time in user's timezone
        if reference_datetime is None:
            reference_datetime = datetime.now(tz)

        # Parse using dateparser
        parsed = dateparser.parse(
            text,
            settings={
                'TIMEZONE': timezone,
                'RETURN_AS_TIMEZONE_AWARE': True,
                'RELATIVE_BASE': reference_datetime,
                'PREFER_DATES_FROM': 'future',
            }
        )

        if parsed:
            # Ensure it's in the correct timezone
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=tz)
            else:
                parsed = parsed.astimezone(tz)

            return parsed

        return None

    except Exception as e:
        logger.error(f"Error parsing datetime '{text}': {e}", exc_info=True)
        return None


async def parse_task_from_nl(
    user_message: str,
    user_timezone: str,
    openai_key: str
) -> Dict[str, Any]:
    """
    Parse task and reminder information from natural language using OpenAI.

    Args:
        user_message: User's natural language input
        user_timezone: User's timezone
        openai_key: OpenAI API key

    Returns:
        Dictionary containing parsed task and reminder data
    """
    try:
        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-5-mini",  # type: ignore[call-arg]
            temperature=0,  # type: ignore[call-arg]
            api_key=openai_key  # type: ignore[call-arg]
        )

        # Get current datetime in user's timezone
        tz = ZoneInfo(user_timezone)
        current_datetime = datetime.now(tz)

        # Format system prompt with context
        system_prompt = TASK_PARSER_SYSTEM_PROMPT.format(
            current_datetime=current_datetime.strftime("%Y-%m-%d %H:%M:%S %Z"),
            user_timezone=user_timezone
        )

        # Create prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{user_message}")
        ])

        # Create chain
        chain = prompt | llm

        # Invoke
        response = await chain.ainvoke({
            "user_message": user_message
        })

        # Parse JSON response
        # Handle both string and list content types
        if isinstance(response.content, list):  # type: ignore[attr-defined]
            # Get first content item if it's a list
            content_item = response.content[0]  # type: ignore[attr-defined,index]
            if isinstance(content_item, dict):
                content = str(content_item.get('text', '')).strip()
            else:
                content = str(content_item).strip()
        else:
            content = str(response.content).strip()  # type: ignore[attr-defined]

        # Remove markdown code blocks if present
        if content.startswith("```"):
            # Extract JSON from markdown
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

        parsed_data = json.loads(content)

        # Parse datetime strings to datetime objects
        if "task_datetime" in parsed_data and parsed_data["task_datetime"]:
            parsed_data["task_datetime"] = parse_datetime_with_context(
                parsed_data["task_datetime"],
                user_timezone,
                current_datetime
            )

        if "reminder_time" in parsed_data and parsed_data["reminder_time"]:
            parsed_data["reminder_time"] = parse_datetime_with_context(
                parsed_data["reminder_time"],
                user_timezone,
                current_datetime
            )

        # Calculate default reminder if not specified
        if parsed_data.get("task_datetime") and not parsed_data.get("reminder_time"):
            parsed_data["reminder_time"] = parsed_data["task_datetime"] - timedelta(minutes=15)

        logger.info(f"Successfully parsed task from NL: {parsed_data.get('task_title')}")
        return parsed_data

    except Exception as e:
        logger.error(f"Error parsing task from NL: {e}", exc_info=True)
        return {
            "error": str(e),
            "task_title": None
        }


def format_datetime_human_readable(dt: datetime, timezone: str) -> str:
    """
    Format datetime in a human-readable way.

    Args:
        dt: Datetime to format
        timezone: User's timezone

    Returns:
        Human-readable datetime string
    """
    try:
        tz = ZoneInfo(timezone)

        # Convert to user's timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        dt_local = dt.astimezone(tz)

        # Get current date in user's timezone
        now = datetime.now(tz).date()
        dt_date = dt_local.date()

        # Determine day description
        if dt_date == now:
            day_str = "today"
        elif dt_date == now + timedelta(days=1):
            day_str = "tomorrow"
        elif dt_date == now - timedelta(days=1):
            day_str = "yesterday"
        elif dt_date < now + timedelta(days=7):
            day_str = dt_local.strftime("%A")  # Day name
        else:
            day_str = dt_local.strftime("%B %d")  # Month day

        # Format time
        time_str = dt_local.strftime("%I:%M %p").lstrip("0")

        return f"{day_str} at {time_str}"

    except Exception as e:
        logger.error(f"Error formatting datetime: {e}", exc_info=True)
        return str(dt)


def generate_confirmation_message(
    task_title: str,
    task_datetime: datetime,
    reminder_time: datetime,
    timezone: str,
    description: Optional[str] = None
) -> str:
    """
    Generate a natural confirmation message for the user.

    Args:
        task_title: Title of the task
        task_datetime: When the task is due
        reminder_time: When to send reminder
        timezone: User's timezone
        description: Optional task description

    Returns:
        Confirmation message string
    """
    try:
        task_time_str = format_datetime_human_readable(task_datetime, timezone)
        reminder_time_str = format_datetime_human_readable(reminder_time, timezone)

        message = f"Should I add task **{task_title}** for {task_time_str}?"

        if description:
            message += f"\n\n📝 Details: {description}"

        message += f"\n\n🔔 I'll remind you at {reminder_time_str}."
        message += f"\n\nReply **Yes** to confirm or tell me what to change."

        return message

    except Exception as e:
        logger.error(f"Error generating confirmation message: {e}", exc_info=True)
        return "Should I create this task? Reply Yes to confirm."
