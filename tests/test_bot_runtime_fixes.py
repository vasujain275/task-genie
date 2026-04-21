from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


class FakeUser:
    def __init__(self):
        self.id = 101
        self.first_name = "Ana"
        self.username = "ana"


class FakeMessage:
    def __init__(self, from_user=None):
        self.from_user = from_user
        self.answers = []
        self.deleted = False
        self.delete_raises = None
        self.text = None

    async def answer(self, text, reply_markup=None, **kwargs):
        self.answers.append((text, reply_markup, kwargs))

    async def delete(self):
        if self.delete_raises:
            raise self.delete_raises
        self.deleted = True


class FakeState:
    def __init__(self):
        self.state = None
        self.cleared = False

    async def set_state(self, value):
        self.state = value

    async def clear(self):
        self.cleared = True
        self.state = None


class FakeStatistics:
    def __init__(self, total_tasks=0, completed_tasks=0, total_reminders=0):
        self.total_tasks = total_tasks
        self.completed_tasks = completed_tasks
        self.total_reminders = total_reminders


def test_start_keeps_returning_user_in_active_mode(monkeypatch):
    from app.bot.handlers import start as start_module

    user = SimpleNamespace(
        telegram_id=101,
        name="Ana",
        timezone="UTC",
        openai_key="key",
    )

    async def get_or_create(*args, **kwargs):
        return user

    monkeypatch.setattr(start_module.User, "get_or_create", get_or_create)

    message = FakeMessage(from_user=FakeUser())
    state = FakeState()

    asyncio.run(start_module.start_handler(message, state))

    assert state.state is not None
    assert message.answers


def test_start_new_user_without_key_gets_setup_flow(monkeypatch):
    from app.bot.handlers import start as start_module

    user = SimpleNamespace(
        telegram_id=202,
        name="New User",
        timezone="UTC",
        openai_key=None,
    )

    async def get_or_create(*args, **kwargs):
        return user

    monkeypatch.setattr(start_module.User, "get_or_create", get_or_create)

    message = FakeMessage(from_user=FakeUser())
    state = FakeState()

    asyncio.run(start_module.start_handler(message, state))

    assert state.cleared is True
    assert state.state is None
    assert message.answers
    text, reply_markup, _ = message.answers[0]
    assert "First Time Setup Required" in text
    assert (
        reply_markup.kwargs["inline_keyboard"][0][0].kwargs["callback_data"]
        == "setup_timezone"
    )


def test_dispatcher_uses_full_redis_url(monkeypatch):
    from app.bot import dispatcher as dispatcher_module

    captured = {}

    def fake_from_url(url, *args, **kwargs):
        captured["url"] = url
        return SimpleNamespace(url=url)

    monkeypatch.setattr(dispatcher_module.RedisStorage, "from_url", fake_from_url)
    monkeypatch.setattr(
        dispatcher_module.settings, "REDIS_URL", "redis://localhost:6379/5"
    )

    dp = dispatcher_module.setup_dispatcher()

    assert dp.storage.url == "redis://localhost:6379/5"
    assert captured["url"] == "redis://localhost:6379/5"


def test_dispatcher_registers_routers_in_specific_order(monkeypatch):
    from app.bot import dispatcher as dispatcher_module

    class FakeDispatcher:
        def __init__(self, storage):
            self.storage = storage
            self.routers = []

        def include_router(self, router):
            self.routers.append(router)

    monkeypatch.setattr(
        dispatcher_module.RedisStorage,
        "from_url",
        lambda *args, **kwargs: SimpleNamespace(url=args[0]),
    )
    monkeypatch.setattr(dispatcher_module, "Dispatcher", FakeDispatcher)

    dp = dispatcher_module.setup_dispatcher()

    assert dp.routers == [
        dispatcher_module.start.router,
        dispatcher_module.stats.router,
        dispatcher_module.settings_handler.router,
        dispatcher_module.conversation.router,
    ]


def test_stats_handler_uses_application_service(monkeypatch):
    from app.bot.handlers import stats as stats_module

    called = {}

    class Service:
        async def get_user_statistics(self, telegram_id):
            called["telegram_id"] = telegram_id
            return FakeStatistics(total_tasks=3, completed_tasks=2, total_reminders=1)

    monkeypatch.setattr(stats_module, "stats_service", Service())

    message = FakeMessage(from_user=FakeUser())

    asyncio.run(stats_module.stats_handler(message))

    assert called["telegram_id"] == 101
    assert message.answers[0][0].startswith("📊 <b>Your Statistics</b>")
    assert "Total Tasks:</b> 3" in message.answers[0][0]
    assert message.answers[0][2]["parse_mode"] == "HTML"


def test_settings_command_uses_markdown_rendering(monkeypatch):
    from app.bot.handlers import settings as settings_module

    class UserRecord(SimpleNamespace):
        pass

    async def get_user(_uid):
        return UserRecord(
            id="u1", telegram_id=101, name="Ana", timezone="UTC", openai_key=None
        )

    monkeypatch.setattr(settings_module.User, "get_by_telegram_id", get_user)

    message = FakeMessage(from_user=FakeUser())
    state = FakeState()

    asyncio.run(settings_module.settings_command_handler(message, state))

    assert message.answers[0][2]["parse_mode"] == "HTML"


def test_settings_accepts_non_sk_api_keys(monkeypatch):
    from app.bot.handlers import settings as settings_module

    saved = {}

    class UserRecord(SimpleNamespace):
        async def save(self):
            saved["key"] = self.openai_key

    async def get_user(_uid):
        return UserRecord(
            id="u1", telegram_id=101, name="Ana", timezone="UTC", openai_key=None
        )

    monkeypatch.setattr(settings_module.User, "get_by_telegram_id", get_user)

    message = FakeMessage(from_user=FakeUser())
    message.text = "abcde123456789012345"
    state = FakeState()

    asyncio.run(settings_module.receive_apikey_handler(message, state))

    assert message.deleted is True
    assert state.cleared is True
    assert saved["key"] == "abcde123456789012345"


def test_settings_deletes_message_after_successful_save(monkeypatch):
    from app.bot.handlers import settings as settings_module

    order = []

    class UserRecord(SimpleNamespace):
        async def save(self):
            order.append("save")

    async def get_user(_uid):
        return UserRecord(
            id="u1", telegram_id=101, name="Ana", timezone="UTC", openai_key=None
        )

    monkeypatch.setattr(settings_module.User, "get_by_telegram_id", get_user)

    message = FakeMessage(from_user=FakeUser())
    message.text = "abcde123456789012345"

    async def delete():
        order.append("delete")
        message.deleted = True

    message.delete = delete
    state = FakeState()

    asyncio.run(settings_module.receive_apikey_handler(message, state))

    assert order == ["save", "delete"]
    assert message.deleted is True


def test_settings_ignores_delete_failure_after_save(monkeypatch):
    from app.bot.handlers import settings as settings_module

    saved = {}

    class UserRecord(SimpleNamespace):
        async def save(self):
            saved["key"] = self.openai_key

    async def get_user(_uid):
        return UserRecord(
            id="u1", telegram_id=101, name="Ana", timezone="UTC", openai_key=None
        )

    monkeypatch.setattr(settings_module.User, "get_by_telegram_id", get_user)

    message = FakeMessage(from_user=FakeUser())
    message.text = "abcde123456789012345"
    message.delete_raises = RuntimeError("delete failed")
    state = FakeState()

    asyncio.run(settings_module.receive_apikey_handler(message, state))

    assert saved["key"] == "abcde123456789012345"
    assert state.cleared is True
    assert message.deleted is False
    assert message.answers[0][0].startswith("✅ <b>Setup Complete!</b>")


def test_settings_rejects_empty_or_short_api_keys(monkeypatch):
    from app.bot.handlers import settings as settings_module

    message = FakeMessage(from_user=FakeUser())
    message.text = " short "
    state = FakeState()

    asyncio.run(settings_module.receive_apikey_handler(message, state))

    assert message.deleted is False
    assert state.cleared is False
    assert (
        message.answers[0][0]
        == "⚠️ That doesn't look like a valid API key. Please check and try again."
    )


def test_conversation_turn_retains_history_for_fourteen_days():
    from app.models import conversation_turn

    assert conversation_turn.CONVERSATION_TURN_RETENTION_DAYS == 14


def test_webhook_rejects_bad_secret_and_bad_payload(monkeypatch):
    import sys
    import types

    reminder_scheduler = types.ModuleType("app.services.reminder_scheduler")
    reminder_scheduler.start_reminder_scheduler = lambda: None
    reminder_scheduler.stop_reminder_scheduler = lambda: None
    sys.modules["app.services.reminder_scheduler"] = reminder_scheduler

    from app import main as main_module

    monkeypatch.setattr(main_module.settings, "TELEGRAM_WEBHOOK_SECRET_TOKEN", "secret")

    class FakeApp:
        state = SimpleNamespace(dp=SimpleNamespace())

    class BadRequest:
        app = FakeApp()
        headers = {"X-Telegram-Bot-Api-Secret-Token": "wrong"}

        async def json(self):
            return {"update_id": 1}

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(
            main_module.webhook(
                BadRequest(), SimpleNamespace(add_task=lambda *args, **kwargs: None)
            )
        )
    assert excinfo.value.status_code == 403

    class InvalidJsonRequest:
        app = FakeApp()
        headers = {"X-Telegram-Bot-Api-Secret-Token": "secret"}

        async def json(self):
            raise ValueError("bad json")

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(
            main_module.webhook(
                InvalidJsonRequest(),
                SimpleNamespace(add_task=lambda *args, **kwargs: None),
            )
        )
    assert excinfo.value.status_code == 400


def test_webhook_rejects_missing_dispatcher_state(monkeypatch):
    import sys
    import types

    reminder_scheduler = types.ModuleType("app.services.reminder_scheduler")
    reminder_scheduler.start_reminder_scheduler = lambda: None
    reminder_scheduler.stop_reminder_scheduler = lambda: None
    sys.modules["app.services.reminder_scheduler"] = reminder_scheduler

    from app import main as main_module

    monkeypatch.setattr(main_module.settings, "TELEGRAM_WEBHOOK_SECRET_TOKEN", "secret")

    class FakeRequest:
        app = SimpleNamespace(state=SimpleNamespace())
        headers = {"X-Telegram-Bot-Api-Secret-Token": "secret"}

        async def json(self):
            return {"update_id": 1}

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(
            main_module.webhook(
                FakeRequest(), SimpleNamespace(add_task=lambda *args, **kwargs: None)
            )
        )

    assert excinfo.value.status_code == 500
    assert excinfo.value.detail == "Dispatcher is not configured"


def test_webhook_schedules_updates_and_validates_secret(monkeypatch):
    import sys
    import types

    reminder_scheduler = types.ModuleType("app.services.reminder_scheduler")
    reminder_scheduler.start_reminder_scheduler = lambda: None
    reminder_scheduler.stop_reminder_scheduler = lambda: None
    sys.modules["app.services.reminder_scheduler"] = reminder_scheduler

    from app import main as main_module

    monkeypatch.setattr(main_module.settings, "TELEGRAM_WEBHOOK_SECRET_TOKEN", "secret")

    captured = {}

    class FakeUpdate:
        def __init__(self, **data):
            captured["update"] = data

    monkeypatch.setattr(main_module.types, "Update", FakeUpdate)

    class FakeDP:
        pass

    tasks = []

    class FakeBackgroundTasks:
        def add_task(self, func, *args):
            tasks.append((func, args))

    class FakeRequest:
        app = SimpleNamespace(state=SimpleNamespace(dp=FakeDP()))
        headers = {"X-Telegram-Bot-Api-Secret-Token": "secret"}

        async def json(self):
            return {"update_id": 1}

    result = asyncio.run(main_module.webhook(FakeRequest(), FakeBackgroundTasks()))

    assert result == {"ok": True}
    assert captured["update"] == {"update_id": 1}
    assert tasks and tasks[0][1][1] is FakeRequest.app.state.dp
