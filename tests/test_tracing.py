from __future__ import annotations

import asyncio

import pytest

from app.ai.engine import tracing
from app.ai.engine.flow import PocketFlowConversationFlow
from app.ai.engine.llm import LiteLLMAdapter
from app.application.contracts import ConversationRequest


def test_tracing_disabled_by_default():
    assert tracing.tracing_enabled() is False
    assert tracing.trace_config()["enabled"] is False


def test_trace_context_and_sanitization(monkeypatch):
    monkeypatch.setattr(tracing.settings, "TRACING_ENABLED", True)
    monkeypatch.setattr(tracing.settings, "LANGFUSE_PUBLIC_KEY", "pub")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_SECRET_KEY", "sec")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_HOST", "https://cloud.langfuse.com")
    ctx = tracing.build_trace_context(
        trace_id="trace-1", session_id="s-1", user_id="u-1", channel="telegram"
    )
    assert ctx.enabled is True
    request_meta = tracing.sanitize_request_state(
        trace_id="trace-1",
        session_id="s-1",
        user_id="u-1",
        channel="telegram",
        model="gpt-5-nano",
        request_text="secret text",
        recent_turns_count=3,
        history_summary="summary",
    )
    assert request_meta.request_text_length == len("secret text")
    assert request_meta.has_history_summary is True


def test_sanitizers_redact_payloads():
    request_message = tracing.sanitize_request_message(
        request_text="top secret",
        history_summary="summary",
        clarification_hint="hint",
    )
    result = tracing.sanitize_result(
        type("Result", (), {"kind": "completed", "message": "done", "data": {"x": 1}})()
    )
    llm_messages = tracing.sanitize_llm_messages(
        [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "ok"}]
    )

    assert request_message == {
        "request_text_length": 10,
        "has_history_summary": True,
        "has_clarification_hint": True,
    }
    assert result == {
        "kind": "completed",
        "message_length": 4,
        "has_interaction": False,
        "interaction_kind": None,
        "choices_count": 0,
        "has_data": True,
    }
    assert llm_messages == {
        "message_count": 2,
        "roles": ["user", "assistant"],
        "content_lengths": [5, 2],
    }


def test_llm_sanitizes_trace_metadata(monkeypatch):
    captured = {}

    monkeypatch.setattr(tracing, "get_active_trace_context", lambda: None)

    class FakeSpan:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        def update(self, *args, **kwargs):
            captured["update"] = (args, kwargs)

    class FakeClient:
        def span(self, **kwargs):
            captured["span"] = kwargs
            return FakeSpan()

    async def fake_completion(**kwargs):
        captured["completion"] = kwargs
        return type(
            "Resp",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {
                            "message": type(
                                "Msg", (), {"content": '{"intent":"chat"}'}
                            )()
                        },
                    )()
                ]
            },
        )()

    monkeypatch.setattr(tracing, "tracing_enabled", lambda: True)
    monkeypatch.setattr(tracing, "get_trace_client", lambda: FakeClient())
    monkeypatch.setattr("app.ai.engine.llm.acompletion", fake_completion)

    tracing._trace_client = None

    adapter = LiteLLMAdapter("gpt-5-nano")
    result = asyncio.run(
        adapter.complete_json(
            messages=[{"role": "user", "content": "hello"}], api_key="key", schema=None
        )
    )
    assert result["intent"] == "chat"
    assert captured["span"]["metadata"]["message_count"] == 1
    assert captured["completion"]["api_key"] == "key"


def test_llm_span_failure_marks_error(monkeypatch):
    captured = {}

    class FakeSpan:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        def update(self, payload):
            captured.setdefault("updates", []).append(payload)

    class FakeClient:
        def span(self, **kwargs):
            captured["span"] = kwargs
            return FakeSpan()

    async def exploding_completion(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(tracing, "tracing_enabled", lambda: True)
    monkeypatch.setattr(tracing, "get_trace_client", lambda: FakeClient())
    monkeypatch.setattr("app.ai.engine.llm.acompletion", exploding_completion)
    tracing._trace_client = None

    adapter = LiteLLMAdapter("gpt-5-nano")
    with pytest.raises(RuntimeError):
        asyncio.run(
            adapter.complete_text(
                messages=[{"role": "user", "content": "hi"}], api_key="key"
            )
        )

    assert captured["updates"][0] == {"success": False, "error": True}


def test_trace_context_has_non_empty_trace_id(monkeypatch):
    monkeypatch.setattr(tracing.settings, "TRACING_ENABLED", True)
    monkeypatch.setattr(tracing.settings, "LANGFUSE_PUBLIC_KEY", "pub")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_SECRET_KEY", "sec")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_HOST", "https://cloud.langfuse.com")

    class FakeSpan:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

    class FakeClient:
        def span(self, **kwargs):
            captured["span"] = kwargs
            return FakeSpan()

    captured = {}
    monkeypatch.setattr(tracing, "get_trace_client", lambda: FakeClient())

    async def run():
        async with tracing.request_trace(
            name="test",
            trace_id="",
            session_id="s-1",
            user_id="u-1",
            metadata={"channel": "telegram"},
        ):
            assert tracing.get_active_trace_context().trace_id == "telegram:s-1"

    asyncio.run(run())
    assert captured["span"]["trace_id"] == "telegram:s-1"


def test_trace_context_does_not_double_prefix_prefixed_session(monkeypatch):
    monkeypatch.setattr(tracing.settings, "TRACING_ENABLED", True)
    monkeypatch.setattr(tracing.settings, "LANGFUSE_PUBLIC_KEY", "pub")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_SECRET_KEY", "sec")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_HOST", "https://cloud.langfuse.com")

    class FakeSpan:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

    class FakeClient:
        def span(self, **kwargs):
            captured["span"] = kwargs
            return FakeSpan()

    captured = {}
    monkeypatch.setattr(tracing, "get_trace_client", lambda: FakeClient())

    async def run():
        async with tracing.request_trace(
            name="test",
            trace_id="",
            session_id="telegram:s-1",
            user_id="u-1",
            metadata={"channel": "telegram"},
        ):
            assert tracing.get_active_trace_context().trace_id == "telegram:s-1"

    asyncio.run(run())
    assert captured["span"]["trace_id"] == "telegram:s-1"


def test_flow_generate_smoke(monkeypatch):
    flow = PocketFlowConversationFlow.build(model="test-model")

    async def fake_completion(**_kwargs):
        return type(
            "Resp",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {
                            "message": type(
                                "Msg", (), {"content": '{"intent":"chat"}'}
                            )()
                        },
                    )()
                ]
            },
        )()

    flow.plan_intent._llm.complete_json = fake_completion
    flow.execute_intent._services = {"create_task": lambda **_kwargs: None}

    class FakeFlow:
        async def run_async(self, shared):
            shared["response"] = type(
                "Resp",
                (),
                {"message": "ok", "kind": "completed", "interaction": None, "data": {}},
            )()

    flow.flow = FakeFlow()

    request = ConversationRequest(
        actor_id=1,
        user_name="Ana",
        user_timezone="UTC",
        text="hi",
        openai_key="key",
        channel="telegram",
        session_id="s",
        trace_id="trace",
    )
    response = asyncio.run(flow.generate(request))
    assert response.kind == "completed"
    assert response.message == "ok"


def test_pocketflow_trace_client_gates_by_env(monkeypatch):
    monkeypatch.setattr(tracing.settings, "TRACING_ENABLED", False)
    monkeypatch.setattr(tracing.settings, "LANGFUSE_PUBLIC_KEY", "pub")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_SECRET_KEY", "sec")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_HOST", "https://cloud.langfuse.com")
    tracing._trace_client = None
    assert tracing.get_trace_client().__class__.__name__ == "NullTraceClient"
