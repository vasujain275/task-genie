from __future__ import annotations

from typing import Any, Literal
from datetime import datetime

try:  # pragma: no cover - dependency fallback for tests
    from pydantic import BaseModel, Field, field_validator, model_validator
except Exception:  # pragma: no cover

    class BaseModel:
        def __init__(self, **data: Any):
            for key, value in data.items():
                setattr(self, key, value)

    def Field(default=None, **_kwargs):
        return default

    def field_validator(*_fields, **_kwargs):
        def decorator(func):
            return func

        return decorator

    def model_validator(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


SupportedIntent = Literal[
    "chat",
    "create_task",
    "edit_task",
    "mark_done",
    "delete_task",
    "list_tasks",
    "get_stats",
    "clarify",
]


class PlannerPlan(BaseModel):
    intent: SupportedIntent
    message: str | None = None
    task_reference: str | None = None
    task_title: str | None = None
    task_description: str | None = None
    task_datetime: str | None = None
    priority: Literal["low", "medium", "high"] | None = None
    tags: list[str] = Field(default_factory=list)
    status: Literal["pending", "done"] | None = None
    limit: int | None = None
    clarification_question: str | None = None
    updates: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "task_reference", "task_title", "message", "clarification_question"
    )
    @classmethod
    def _strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def _validate_intent_payload(self):
        if self.intent == "create_task" and not self.task_title:
            raise ValueError("task_title is required for create_task")
        if self.intent == "create_task" and not self.task_datetime:
            raise ValueError("task_datetime is required for create_task")
        if self.intent == "clarify" and not self.clarification_question:
            raise ValueError("clarification_question is required for clarify")
        if (
            self.intent in {"edit_task", "mark_done", "delete_task"}
            and not self.task_reference
        ):
            raise ValueError("task_reference is required for task mutations")
        return self

    def parsed_task_datetime(self) -> datetime | None:
        if not self.task_datetime:
            return None
        return datetime.fromisoformat(self.task_datetime)

    @classmethod
    def model_validate(cls, data: Any):
        if not isinstance(data, dict):
            raise TypeError("PlannerPlan expects a dict")
        if "tags" not in data or data["tags"] is None:
            data = {**data, "tags": []}
        instance = cls(**data)
        instance._validate_intent_payload()
        return instance

    @classmethod
    def model_json_schema(cls):
        return {
            "type": "object",
            "properties": {
                "intent": {"type": "string"},
                "message": {"type": ["string", "null"]},
                "task_reference": {"type": ["string", "null"]},
                "task_title": {"type": ["string", "null"]},
                "task_description": {"type": ["string", "null"]},
                "task_datetime": {"type": ["string", "null"]},
                "priority": {"type": ["string", "null"]},
                "tags": {"type": "array"},
                "status": {"type": ["string", "null"]},
                "limit": {"type": ["integer", "null"]},
                "clarification_question": {"type": ["string", "null"]},
                "updates": {"type": "object"},
            },
            "required": ["intent"],
        }
