from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.application.contracts import ApplicationResult
from app.bot.handlers import conversation
from app.bot.adapters.conversation import (
    build_conversation_request,
    build_request_context,
)


@dataclass
class FakeFromUser:
    id: int
    language_code: str = "en"


class FakeBot:
    def __init__(self):
        self.actions = []

    async def send_chat_action(self, chat_id, action):
        self.actions.append((chat_id, action))


class FakeMessage:
    def __init__(self, *, from_user=None, text=None):
        self.from_user = from_user
        self.text = text
        self.chat = type("Chat", (), {"id": 42})()
        self.bot = FakeBot()
        self.answers = []

    async def answer(self, text, parse_mode=None):
        self.answers.append((text, parse_mode))


class FallbackMessage(FakeMessage):
    async def answer(self, text, parse_mode=None):
        if parse_mode is not None:
            raise RuntimeError("markdown failed")
        await super().answer(text, parse_mode=parse_mode)


class FakeState:
    pass


def test_handler_delegates_to_service_and_presenter(monkeypatch):
    message = FakeMessage(from_user=FakeFromUser(101), text="hi")
    captured = {}

    monkeypatch.setattr(
        conversation,
        "build_request_context",
        lambda msg: type("Ctx", (), {"actor_id": "101"})(),
    )

    async def handle_message(context, text):
        captured["context"] = context.actor_id
        captured["text"] = text
        return ApplicationResult(kind="completed", message="ok")

    monkeypatch.setattr(
        conversation.conversation_service, "handle_message", handle_message
    )

    asyncio.run(conversation.handle_conversation(message, FakeState()))

    assert captured == {"context": "101", "text": "hi"}
    assert message.bot.actions == [(42, "typing")]
    assert message.answers == [("ok", "Markdown")]


def test_handler_missing_message_text(monkeypatch):
    message = FakeMessage(from_user=FakeFromUser(101), text=None)

    asyncio.run(conversation.handle_conversation(message, FakeState()))

    assert message.answers == [("Please send a text message.", None)]


def test_handler_missing_user(monkeypatch):
    message = FakeMessage(from_user=None, text="hi")

    asyncio.run(conversation.handle_conversation(message, FakeState()))

    assert message.answers == [("User information not available.", None)]


def test_request_context_mapping():
    message = FakeMessage(from_user=FakeFromUser(101, language_code="uk"), text="hi")
    message.chat.id = 99
    message.message_id = 7
    message.from_user.timezone = "Europe/Kyiv"

    context = build_request_context(message)

    assert context.actor_id == "101"
    assert context.session_id == "99"
    assert context.trace_id == "telegram:99:7"
    assert context.locale == "uk"
    assert context.timezone == "Europe/Kyiv"


def test_conversation_request_mapping():
    context = build_request_context(FakeMessage(from_user=FakeFromUser(101), text="hi"))
    user = type("User", (), {"name": "Ana", "timezone": "UTC", "openai_key": "k"})()

    request = build_conversation_request(context, user, "hello")

    assert request.actor_id == 101
    assert request.user_name == "Ana"
    assert request.text == "hello"


def test_presenter_falls_back_without_markdown(monkeypatch):
    message = FallbackMessage(from_user=FakeFromUser(101), text="hi")
    result = ApplicationResult(kind="completed", message="*ok*")

    asyncio.run(conversation.present_application_result(message, result))

    assert message.answers == [("*ok*", None)]


def test_handler_exception_fallback(monkeypatch):
    message = FakeMessage(from_user=FakeFromUser(101), text="hi")

    monkeypatch.setattr(conversation, "build_request_context", lambda _msg: object())
    monkeypatch.setattr(
        conversation.conversation_service,
        "handle_message",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    asyncio.run(conversation.handle_conversation(message, FakeState()))

    assert message.answers == [("Sorry, something went wrong. Please try again.", None)]
