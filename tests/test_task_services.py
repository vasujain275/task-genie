from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from app.ai.services import task_services
from app.ai.services.timezone import convert_utc_to_user_timezone


class FakeLink:
    def __init__(self, user):
        self._user = user

    async def fetch(self):
        return self._user


class FakeUser:
    def __init__(self, telegram_id=101, timezone="Asia/Kolkata", id="user-1"):
        self.telegram_id = telegram_id
        self.timezone = timezone
        self.id = id


class FakeTaskModel:
    user = SimpleNamespace(id=object())
    status = object()


class FakeOwnedTask:
    def __init__(self, *, owner: FakeUser, task_id: str = "task-1", **kwargs):
        self.id = task_id
        self.user = FakeLink(owner)
        self.title = kwargs.get("title", "Task")
        self.description = kwargs.get("description")
        self.task_datetime = kwargs.get(
            "task_datetime", datetime(2026, 4, 16, 4, 0, tzinfo=timezone.utc)
        )
        self.priority = kwargs.get("priority", "medium")
        self.tags = kwargs.get("tags", [])
        self.updated_at = kwargs.get("updated_at")
        self.status = kwargs.get("status", "pending")
        self.saved = False
        self.done = False

    async def save(self):
        self.saved = True

    async def mark_as_done(self):
        self.done = True
        self.status = "done"


class FakeOwnedTaskModel:
    def __init__(self, task):
        self._task = task

    async def get(self, _task_id):
        return self._task


class FakeStatsTaskModel:
    def __init__(self, stats):
        self._stats = stats

    async def get_task_statistics(self, user_id):
        self.user_id = user_id
        return self._stats


def test_create_task_service_happy_path():
    user = FakeUser()

    class UserModel:
        @staticmethod
        async def get_by_telegram_id(_uid):
            return user

    class TaskModel:
        last = None

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.id = "task-1"

        async def insert(self):
            TaskModel.last = self

    result = asyncio.run(
        task_services.create_task(
            user_id=101,
            title="Call mom",
            task_datetime=datetime(2026, 4, 16, 9, 0, tzinfo=timezone.utc),
            user_model=UserModel,
            task_model=TaskModel,
        )
    )

    assert result["success"] is True
    assert result["task_datetime"] == "2026-04-16T14:30:00+05:30"


def test_create_reminder_service_happy_path():
    user = FakeUser()

    class UserModel:
        @staticmethod
        async def get_by_telegram_id(_uid):
            return user

    class TaskModel:
        @staticmethod
        async def get(_task_id):
            return SimpleNamespace(id="task-9")

    class ReminderModel:
        last = None

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.id = "rem-9"

        async def insert(self):
            ReminderModel.last = self

    result = asyncio.run(
        task_services.create_reminder(
            user_id=101,
            task_id="task-9",
            remind_at=datetime(2026, 4, 16, 9, 0, tzinfo=timezone.utc),
            message="Ping",
            user_model=UserModel,
            task_model=TaskModel,
            reminder_model=ReminderModel,
        )
    )

    assert result == {
        "success": True,
        "reminder_id": "rem-9",
        "task_id": "task-9",
        "remind_at": "2026-04-16T14:30:00+05:30",
        "message": "✓ Reminder set",
    }


def test_create_reminder_service_rejects_missing_task():
    user = FakeUser()

    class UserModel:
        @staticmethod
        async def get_by_telegram_id(_uid):
            return user

    class TaskModel:
        @staticmethod
        async def get(_task_id):
            return None

    result = asyncio.run(
        task_services.create_reminder(
            user_id=101,
            task_id="task-missing",
            remind_at=datetime(2026, 4, 16, 9, 0, tzinfo=timezone.utc),
            user_model=UserModel,
            task_model=TaskModel,
        )
    )

    assert result == {"success": False, "error": "Task not found"}


def test_list_tasks_service_formats_timezone():
    user = FakeUser()
    task = SimpleNamespace(
        id="task-2",
        title="Pay rent",
        description="April rent",
        task_datetime=datetime(2026, 4, 16, 4, 0, tzinfo=timezone.utc),
        status="pending",
        priority="medium",
        tags=["home"],
    )

    class Query:
        def find(self, *_args, **_kwargs):
            return self

        def sort(self, *_args, **_kwargs):
            return self

        def limit(self, *_args, **_kwargs):
            return self

        async def to_list(self):
            return [task]

    class UserModel:
        @staticmethod
        async def get_by_telegram_id(_uid):
            return user

    class TaskModel:
        user = SimpleNamespace(id=object())
        status = object()

        @staticmethod
        def find(_expr):
            return Query()

    result = asyncio.run(
        task_services.list_tasks(
            user_id=101, user_model=UserModel, task_model=TaskModel
        )
    )

    assert result["count"] == 1
    assert result["tasks"][0]["task_datetime"] == "2026-04-16T09:30:00+05:30"


def test_delete_task_service_cascades_reminders():
    owner = FakeUser()
    task = SimpleNamespace(id="task-4", title="Archive files", user=FakeLink(owner))
    deleted = []

    async def delete_task():
        deleted.append("task")

    class Reminder:
        @staticmethod
        async def get_reminders_by_task(_task_id):
            return [
                SimpleNamespace(delete=lambda: deleted.append("r1")),
                SimpleNamespace(delete=lambda: deleted.append("r2")),
            ]

    class TaskModel:
        @staticmethod
        async def get(_task_id):
            return task

    task.delete = delete_task

    result = asyncio.run(
        task_services.delete_task(
            user_id=101,
            task_id="task-4",
            task_model=TaskModel,
            reminder_model=Reminder,
        )
    )

    assert result == {
        "success": True,
        "task_id": "task-4",
        "reminders_deleted": 2,
        "message": "✓ Deleted (+2 reminders)",
    }
    assert deleted == ["r1", "r2", "task"]


def test_edit_task_service_updates_selected_fields():
    owner = FakeUser()
    task = FakeOwnedTask(owner=owner, task_id="task-3", title="Old")

    result = asyncio.run(
        task_services.edit_task(
            user_id=101,
            task_id="task-3",
            title="New title",
            tags=["new"],
            task_model=FakeOwnedTaskModel(task),
        )
    )

    assert result == {
        "success": True,
        "task_id": "task-3",
        "updated_fields": ["title", "tags"],
        "message": "✓ Updated",
    }
    assert task.saved is True
    assert task.title == "New title"
    assert task.tags == ["new"]


def test_edit_task_service_rejects_non_owner():
    owner = FakeUser(telegram_id=202)
    task = FakeOwnedTask(owner=owner, task_id="task-3")

    result = asyncio.run(
        task_services.edit_task(
            user_id=101,
            task_id="task-3",
            title="New title",
            task_model=FakeOwnedTaskModel(task),
        )
    )

    assert result == {"success": False, "error": "Task not found"}


def test_mark_task_done_service_marks_owned_task_done():
    owner = FakeUser()
    task = FakeOwnedTask(owner=owner, task_id="task-1")

    result = asyncio.run(
        task_services.mark_task_done(
            user_id=101,
            task_id="task-1",
            task_model=FakeOwnedTaskModel(task),
        )
    )

    assert result == {"success": True, "task_id": "task-1", "message": "✓ Done! 🎉"}
    assert task.done is True


def test_mark_task_done_service_rejects_non_owner():
    owner = FakeUser(telegram_id=202)
    task = FakeOwnedTask(owner=owner, task_id="task-1")

    result = asyncio.run(
        task_services.mark_task_done(
            user_id=101,
            task_id="task-1",
            task_model=FakeOwnedTaskModel(task),
        )
    )

    assert result == {"success": False, "error": "Task not found"}


def test_get_task_statistics_service_success():
    user = FakeUser()

    class UserModel:
        @staticmethod
        async def get_by_telegram_id(_uid):
            return user

    stats_model = FakeStatsTaskModel({"total": 5, "pending": 2, "done": 3})

    result = asyncio.run(
        task_services.get_task_statistics(
            user_id=101,
            user_model=UserModel,
            task_model=stats_model,
        )
    )

    assert result == {
        "success": True,
        "statistics": {"total": 5, "pending": 2, "done": 3},
        "message": "✓ Stats",
    }
    assert stats_model.user_id == "user-1"


def test_get_task_statistics_service_rejects_missing_user():
    class UserModel:
        @staticmethod
        async def get_by_telegram_id(_uid):
            return None

    result = asyncio.run(
        task_services.get_task_statistics(
            user_id=101,
            user_model=UserModel,
            task_model=FakeStatsTaskModel({}),
        )
    )

    assert result == {"success": False, "error": "User not found"}


def test_convert_utc_to_user_timezone_falls_back_to_utc():
    dt = datetime(2026, 4, 16, 9, 0, tzinfo=timezone.utc)

    converted = convert_utc_to_user_timezone(dt, "Not/A_Timezone")

    assert converted is not None
    assert converted.isoformat() == "2026-04-16T09:00:00+00:00"
