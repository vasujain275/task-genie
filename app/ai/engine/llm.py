from __future__ import annotations

import json
from typing import Any

from app.ai.engine import tracing as tracing_mod

try:
    from litellm import acompletion  # type: ignore
except Exception:  # pragma: no cover - dependency may be absent in test env

    async def acompletion(*_args: Any, **_kwargs: Any):  # type: ignore
        raise RuntimeError("litellm is required for LLM access")


class LiteLLMAdapter:
    def __init__(self, model: str, api_key: str | None = None):
        self.model = model
        self._api_key = api_key

    def bind_api_key(self, api_key: str) -> "LiteLLMAdapter":
        return LiteLLMAdapter(self.model, api_key)

    async def complete_json(
        self,
        *,
        messages: list[dict[str, str]],
        api_key: str,
        schema: dict[str, Any] | None = None,
        temperature: float = 0,
        trace_context: Any | None = None,
        request_message: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        effective_api_key = api_key or self._api_key
        if effective_api_key:
            kwargs["api_key"] = effective_api_key
        if schema is not None:
            kwargs["response_format"] = {"type": "json_object"}
            kwargs["extra_headers"] = {"X-Response-Schema": json.dumps(schema)}

        trace_client = tracing_mod.get_trace_client()
        span = None
        if trace_client is not None:
            active_context = trace_context or tracing_mod.get_active_trace_context()
            span = trace_client.span(
                name="llm.complete_json",
                metadata={
                    "model": self.model,
                    "call_type": "json",
                    **(
                        {
                            "trace_id": active_context.trace_id,
                            "session_id": active_context.session_id,
                            "user_id": active_context.user_id,
                            "channel": active_context.channel,
                        }
                        if active_context is not None
                        else {}
                    ),
                    **(request_message or {}),
                    **tracing_mod.sanitize_llm_messages(messages),
                },
            )
        try:
            if span is not None:
                async with span:
                    response = await acompletion(**kwargs)
            else:
                response = await acompletion(**kwargs)
        except Exception:
            if span is not None:
                span.update({"success": False, "error": True})
            raise
        if span is not None:
            span.update({"success": True})
        choice = response.choices[0]
        message = getattr(choice, "message", choice)
        content = getattr(message, "content", None)
        if content is None:
            raise ValueError("LLM returned no content")
        if isinstance(content, str):
            return json.loads(content)
        if isinstance(content, dict):
            return content
        raise ValueError(f"Unsupported LLM response content: {type(content)!r}")

    async def complete_text(
        self,
        *,
        messages: list[dict[str, str]],
        api_key: str,
        temperature: float = 0.2,
        trace_context: Any | None = None,
        request_message: dict[str, Any] | None = None,
    ) -> str:
        effective_api_key = api_key or self._api_key
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if effective_api_key:
            kwargs["api_key"] = effective_api_key

        trace_client = tracing_mod.get_trace_client()
        span = None
        if trace_client is not None:
            active_context = trace_context or tracing_mod.get_active_trace_context()
            span = trace_client.span(
                name="llm.complete_text",
                metadata={
                    "model": self.model,
                    "call_type": "text",
                    **(
                        {
                            "trace_id": active_context.trace_id,
                            "session_id": active_context.session_id,
                            "user_id": active_context.user_id,
                            "channel": active_context.channel,
                        }
                        if active_context is not None
                        else {}
                    ),
                    **(request_message or {}),
                    **tracing_mod.sanitize_llm_messages(messages),
                },
            )
        try:
            if span is not None:
                async with span:
                    response = await acompletion(**kwargs)
            else:
                response = await acompletion(**kwargs)
        except Exception:
            if span is not None:
                span.update({"success": False, "error": True})
            raise
        if span is not None:
            span.update({"success": True})
        choice = response.choices[0]
        message = getattr(choice, "message", choice)
        content = getattr(message, "content", None)
        if content is None:
            raise ValueError("LLM returned no content")
        return str(content)
