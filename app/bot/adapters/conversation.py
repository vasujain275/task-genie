from __future__ import annotations

from app.application.context import RequestContext
from app.application.contracts import ApplicationResult, ConversationRequest


def build_request_context(message) -> RequestContext:
    return RequestContext(
        actor_id=str(message.from_user.id),
        channel="telegram",
        session_id=str(message.chat.id),
        timezone=getattr(getattr(message, "from_user", None), "timezone", None)
        or "UTC",
        trace_id=f"telegram:{message.chat.id}:{getattr(message, 'message_id', 'unknown')}",
        locale=getattr(getattr(message, "from_user", None), "language_code", None),
    )


def build_conversation_request(
    context: RequestContext, user, text: str
) -> ConversationRequest:
    return ConversationRequest(
        actor_id=int(context.actor_id),
        user_name=user.name,
        user_timezone=user.timezone,
        text=text,
        openai_key=user.openai_key,
        channel=context.channel,
        session_id=context.session_id,
        trace_id=context.trace_id,
    )


async def present_application_result(message, result: ApplicationResult) -> None:
    try:
        await message.answer(result.message, parse_mode="Markdown")
    except Exception:
        await message.answer(result.message)
