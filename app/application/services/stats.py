from __future__ import annotations

from dataclasses import dataclass

from app.models.reminder import Reminder
from app.models.task import Task
from app.models.user import User


@dataclass(frozen=True)
class UserStatistics:
    total_tasks: int
    completed_tasks: int
    total_reminders: int


class StatsService:
    async def get_user_statistics(self, telegram_id: int) -> UserStatistics | None:
        user = await User.get_by_telegram_id(telegram_id)
        if not user:
            return None

        total_tasks = await Task.find(Task.user.id == user.id).count()  # type: ignore
        completed_tasks = await Task.find(  # type: ignore
            Task.user.id == user.id,
            Task.status == "done",
        ).count()
        total_reminders = await Reminder.find(Reminder.user.id == user.id).count()  # type: ignore

        return UserStatistics(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            total_reminders=total_reminders,
        )
