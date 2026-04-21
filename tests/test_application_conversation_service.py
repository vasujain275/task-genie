from __future__ import annotations

from dataclasses import dataclass
import asyncio
import pytest

from app.ai.services.conversation import PocketFlowConversationResponder
from app.application.context import RequestContext
from app.application.contracts import ConversationResponse
from app.application.services.conversation import ConversationService


@dataclass
class FakeUser:
    telegram_id: int
    openai_key: str | None
    name: str = "Vasu"
    timezone: str = "UTC"


class FakeResponder:
    def __init__(self, response=None, should_raise=False):
        self.response = response
        self.should_raise = should_raise
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        if self.should_raise:
            raise RuntimeError("boom")
        return self.response


def test_service_rejects_missing_user(monkeypatch):
    async def get_user(_uid):
        return None

    monkeypatch.setattr(
        "app.application.services.conversation.User.get_by_telegram_id", get_user
    )

    service = ConversationService()
    result = asyncio.run(
        service.handle_message(
            RequestContext("101", "telegram", "42", "UTC", "trace"), "hi"
        )
    )

    assert result.kind == "rejected"
    assert result.message == "User not found. Please use /start to register."


def test_service_rejects_missing_key(monkeypatch):
    async def get_user(_uid):
        return FakeUser(telegram_id=101, openai_key=None)

    monkeypatch.setattr(
        "app.application.services.conversation.User.get_by_telegram_id", get_user
    )

    service = ConversationService()
    result = asyncio.run(
        service.handle_message(
            RequestContext("101", "telegram", "42", "UTC", "trace"), "hi"
        )
    )

    assert result.kind == "rejected"
    assert "OpenAI API key" in result.message


def test_service_translates_tool_messages(monkeypatch):
    async def get_user(_uid):
        return FakeUser(telegram_id=101, openai_key="key")

    class Responder:
        async def generate(self, request):
            return ConversationResponse(message="✓ Done")

    monkeypatch.setattr(
        "app.application.services.conversation.User.get_by_telegram_id", get_user
    )

    service = ConversationService(responder=Responder())
    result = asyncio.run(
        service.handle_message(
            RequestContext("101", "telegram", "42", "UTC", "trace"), "create task"
        )
    )

    assert result.kind == "completed"
    assert result.message == "✓ Done"


def test_service_uses_responder_and_falls_back_on_missing_message(monkeypatch):
    async def get_user(_uid):
        return FakeUser(telegram_id=101, openai_key="key", name="Ana", timezone="UTC")

    monkeypatch.setattr(
        "app.application.services.conversation.User.get_by_telegram_id", get_user
    )

    responder = FakeResponder(ConversationResponse(message=None))
    service = ConversationService(responder=responder)

    result = asyncio.run(
        service.handle_message(
            RequestContext("101", "telegram", "42", "UTC", "trace"), "hi"
        )
    )

    assert result.kind == "completed"
    assert result.message == "I couldn't process that. Could you try again?"
    assert responder.requests[0].actor_id == 101
    assert responder.requests[0].user_name == "Ana"


def test_responder_handles_malformed_response():
    responder = PocketFlowConversationResponder()

    assert hasattr(responder, "generate")


def test_conversation_service_preserves_interaction(monkeypatch):
    async def get_user(_uid):
        return FakeUser(telegram_id=101, openai_key="key")

    monkeypatch.setattr(
        "app.application.services.conversation.User.get_by_telegram_id", get_user
    )

    interaction = ConversationResponse(
        message="Which task?", kind="needs_clarification"
    )

    class Responder:
        async def generate(self, request):
            return interaction

    service = ConversationService(responder=Responder())
    result = asyncio.run(
        service.handle_message(
            RequestContext("101", "telegram", "42", "UTC", "trace"), "edit it"
        )
    )

    assert result.kind == "needs_clarification"
    assert result.message == "Which task?"


def test_conversation_service_preserves_richer_responder_output(monkeypatch):
    async def get_user(_uid):
        return FakeUser(telegram_id=101, openai_key="key")

    monkeypatch.setattr(
        "app.application.services.conversation.User.get_by_telegram_id", get_user
    )

    interaction = ConversationResponse(
        message=None,
        kind="needs_clarification",
        interaction=None,
        data={"hint": "use task name"},
    )

    class Responder:
        async def generate(self, request):
            return interaction

    service = ConversationService(responder=Responder())
    result = asyncio.run(
        service.handle_message(
            RequestContext("101", "telegram", "42", "UTC", "trace"), "edit it"
        )
    )

    assert result.kind == "needs_clarification"
    assert result.message == "I couldn't process that. Could you try again?"
    assert result.data == {"hint": "use task name"}


def test_conversation_service_forwards_trace_id(monkeypatch):
    async def get_user(_uid):
        return FakeUser(telegram_id=101, openai_key="key", name="Ana", timezone="UTC")

    monkeypatch.setattr(
        "app.application.services.conversation.User.get_by_telegram_id", get_user
    )

    responder = FakeResponder(ConversationResponse(message="ok"))
    service = ConversationService(responder=responder)

    asyncio.run(
        service.handle_message(
            RequestContext("101", "telegram", "42", "UTC", "trace-123"), "hi"
        )
    )

    assert responder.requests[0].trace_id == "trace-123"


def test_conversation_service_handles_key_decryption_failure(monkeypatch):
    async def get_user(_uid):
        return FakeUser(telegram_id=101, openai_key="key", name="Ana", timezone="UTC")

    monkeypatch.setattr(
        "app.application.services.conversation.User.get_by_telegram_id", get_user
    )

    from app.ai.services.conversation import APIKeyDecryptionError

    service = ConversationService(responder=FakeResponder(should_raise=True))
    service._responder.should_raise = False

    async def raise_key_error(request):
        raise APIKeyDecryptionError("bad key")

    service._responder.generate = raise_key_error

    result = asyncio.run(
        service.handle_message(
            RequestContext("101", "telegram", "42", "UTC", "trace"), "hi"
        )
    )

    assert result.kind == "rejected"
    assert "reconfigure" in result.message.lower()


def test_service_propagates_responder_failure(monkeypatch):
    async def get_user(_uid):
        return FakeUser(telegram_id=101, openai_key="key")

    monkeypatch.setattr(
        "app.application.services.conversation.User.get_by_telegram_id", get_user
    )

    service = ConversationService(responder=FakeResponder(should_raise=True))

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(
            service.handle_message(
                RequestContext("101", "telegram", "42", "UTC", "trace"), "hi"
            )
        )


def test_responder_uses_pocketflow_flow(monkeypatch):
    captured = {}

    class FakeFlow:
        async def generate(self, request):
            captured["request"] = request
            return ConversationResponse(message="ok")

    monkeypatch.setattr(
        "app.ai.engine.flow.build_conversation_flow",
        lambda: FakeFlow(),
    )

    responder = PocketFlowConversationResponder()
    result = asyncio.run(
        responder.generate(
            type(
                "Req",
                (),
                {
                    "actor_id": 101,
                    "user_name": "Ana",
                    "user_timezone": "UTC",
                    "text": "hi",
                    "openai_key": "encrypted",
                    "channel": "telegram",
                    "session_id": "42",
                },
            )()
        )
    )

    assert result.message == "ok"
    assert captured["request"].openai_key == "encrypted"
    assert captured["request"].trace_id == ""


def test_responder_preserves_trace_id(monkeypatch):
    captured = {}

    class FakeFlow:
        async def generate(self, request):
            captured["request"] = request
            return ConversationResponse(message="ok")

    monkeypatch.setattr(
        "app.ai.engine.flow.build_conversation_flow",
        lambda: FakeFlow(),
    )

    responder = PocketFlowConversationResponder()
    result = asyncio.run(
        responder.generate(
            type(
                "Req",
                (),
                {
                    "actor_id": 101,
                    "user_name": "Ana",
                    "user_timezone": "UTC",
                    "text": "hi",
                    "openai_key": "encrypted",
                    "channel": "telegram",
                    "session_id": "42",
                    "trace_id": "telegram:42:7",
                },
            )()
        )
    )

    assert result.message == "ok"
    assert captured["request"].trace_id == "telegram:42:7"


def test_responder_normalizes_session_fallback(monkeypatch):
    captured = {}

    class FakeFlow:
        async def generate(self, request):
            captured["request"] = request
            return ConversationResponse(message="ok")

    monkeypatch.setattr(
        "app.ai.engine.flow.build_conversation_flow",
        lambda: FakeFlow(),
    )

    responder = PocketFlowConversationResponder()
    result = asyncio.run(
        responder.generate(
            type(
                "Req",
                (),
                {
                    "actor_id": 101,
                    "user_name": "Ana",
                    "user_timezone": "UTC",
                    "text": "hi",
                    "openai_key": "encrypted",
                    "channel": "telegram",
                    "session_id": "",
                },
            )()
        )
    )

    assert result.message == "ok"
    assert captured["request"].session_id == "telegram:101"
    assert captured["request"].trace_id == ""


def test_responder_decrypts_api_key_before_flow(monkeypatch):
    captured = {}

    class FakeFlow:
        async def generate(self, request):
            captured["request"] = request
            return ConversationResponse(message="ok")

    monkeypatch.setattr(
        "app.ai.engine.flow.build_conversation_flow",
        lambda: FakeFlow(),
    )
    monkeypatch.setattr(
        "app.ai.services.conversation.decrypt_api_key",
        lambda value: f"decrypted:{value}",
    )

    responder = PocketFlowConversationResponder()
    result = asyncio.run(
        responder.generate(
            type(
                "Req",
                (),
                {
                    "actor_id": 101,
                    "user_name": "Ana",
                    "user_timezone": "UTC",
                    "text": "hi",
                    "openai_key": "encrypted",
                    "channel": "telegram",
                    "session_id": "42",
                },
            )()
        )
    )

    assert result.message == "ok"
    assert captured["request"].openai_key == "decrypted:encrypted"
