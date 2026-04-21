from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from contextvars import ContextVar
from typing import Any

from app.config import settings


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    session_id: str
    user_id: str
    channel: str
    enabled: bool


_active_trace_context: ContextVar[TraceContext | None] = ContextVar(
    "active_trace_context", default=None
)


@dataclass(frozen=True)
class SanitizedTraceState:
    trace_id: str
    session_id: str
    user_id: str
    channel: str
    model: str
    intent: str | None = None
    result_kind: str | None = None
    request_text_length: int | None = None
    recent_turns_count: int | None = None
    has_history_summary: bool | None = None


def tracing_enabled() -> bool:
    return settings.tracing_enabled


def build_trace_context(
    *, trace_id: str, session_id: str, user_id: str, channel: str
) -> TraceContext:
    return TraceContext(
        trace_id=trace_id,
        session_id=session_id,
        user_id=user_id,
        channel=channel,
        enabled=tracing_enabled(),
    )


def normalize_session_id(channel: str, session_id: str, user_id: str | int) -> str:
    normalized_session_id = session_id.strip()
    if normalized_session_id:
        return normalized_session_id
    return f"{channel}:{user_id}"


def normalize_trace_id(
    *, trace_id: str, session_id: str, user_id: str | int, channel: str
) -> str:
    normalized_trace_id = trace_id.strip()
    if normalized_trace_id:
        return normalized_trace_id

    normalized_session_id = normalize_session_id(channel, session_id, user_id)
    if normalized_session_id.startswith(f"{channel}:"):
        return normalized_session_id
    return f"{channel}:{normalized_session_id}"


def get_active_trace_context() -> TraceContext | None:
    return _active_trace_context.get()


def _normalize_trace_metadata(
    *, trace_id: str, session_id: str, user_id: str, channel: str
) -> TraceContext:
    normalized_trace_id = normalize_trace_id(
        trace_id=trace_id,
        session_id=session_id,
        user_id=user_id,
        channel=channel,
    )
    return build_trace_context(
        trace_id=normalized_trace_id,
        session_id=session_id,
        user_id=user_id,
        channel=channel,
    )


def sanitize_request_state(
    *,
    trace_id: str,
    session_id: str,
    user_id: str,
    channel: str,
    model: str,
    request_text: str,
    recent_turns_count: int,
    history_summary: str | None,
) -> SanitizedTraceState:
    return SanitizedTraceState(
        trace_id=trace_id,
        session_id=session_id,
        user_id=user_id,
        channel=channel,
        model=model,
        request_text_length=len(request_text),
        recent_turns_count=recent_turns_count,
        has_history_summary=bool(history_summary),
    )


def sanitize_request_message(
    *,
    request_text: str,
    history_summary: str | None = None,
    clarification_hint: str | None = None,
) -> dict[str, Any]:
    return {
        "request_text_length": len(request_text),
        "has_history_summary": bool(history_summary),
        "has_clarification_hint": bool(clarification_hint),
    }


def sanitize_llm_messages(messages: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "message_count": len(messages),
        "roles": [message.get("role", "") for message in messages],
        "content_lengths": [len(message.get("content", "")) for message in messages],
    }


def sanitize_result(result: Any) -> dict[str, Any]:
    kind = getattr(result, "kind", None) if result is not None else None
    message = getattr(result, "message", None) if result is not None else None
    interaction = getattr(result, "interaction", None) if result is not None else None
    return {
        "kind": kind,
        "message_length": len(message or "") if message is not None else None,
        "has_interaction": interaction is not None,
        "interaction_kind": getattr(interaction, "kind", None),
        "choices_count": len(getattr(interaction, "choices", ()) or ()),
        "has_data": bool(getattr(result, "data", None)),
    }


class NullTraceSpan:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    def update(self, *_args, **_kwargs):
        return None


class NullTraceClient:
    def span(self, *_args, **_kwargs):
        return NullTraceSpan()

    def flush(self):
        return None


_trace_client: Any = None


def get_trace_client() -> Any:
    global _trace_client
    if not tracing_enabled():
        return NullTraceClient()
    if _trace_client is None:
        try:
            from langfuse import Langfuse
        except Exception:
            return NullTraceClient()
        _trace_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            release=settings.LANGFUSE_PROJECT or None,
        )
    return _trace_client


def trace_config() -> dict[str, Any]:
    return {
        "enabled": tracing_enabled(),
        "host": settings.LANGFUSE_HOST or None,
        "project": settings.LANGFUSE_PROJECT or None,
    }


@asynccontextmanager
async def request_trace(
    *, name: str, trace_id: str, session_id: str, user_id: str, metadata: dict[str, Any]
):
    client = get_trace_client()
    active_context = _normalize_trace_metadata(
        trace_id=trace_id,
        session_id=session_id,
        user_id=user_id,
        channel=str(metadata.get("channel", "")),
    )
    token = _active_trace_context.set(active_context)
    span = client.span(
        name=name,
        trace_id=active_context.trace_id,
        session_id=active_context.session_id,
        user_id=active_context.user_id,
        metadata=metadata,
    )
    try:
        async with span:
            yield span
    finally:
        _active_trace_context.reset(token)


def flush_traces() -> None:
    client = get_trace_client()
    flush = getattr(client, "flush", None)
    if callable(flush):
        flush()
