from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Protocol, Sequence


InteractionKind = Literal["none", "clarification"]
ApplicationResultKind = Literal["completed", "rejected", "needs_clarification"]


@dataclass(frozen=True)
class ApplicationInteraction:
    kind: InteractionKind
    choices: Sequence[str] = ()
    expected_input: Optional[str] = None


@dataclass(frozen=True)
class ApplicationResult:
    kind: ApplicationResultKind
    message: str
    interaction: Optional[ApplicationInteraction] = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversationRequest:
    actor_id: int
    user_name: str
    user_timezone: str
    text: str
    openai_key: str
    channel: str = "telegram"
    session_id: str = ""
    trace_id: str = ""


@dataclass(frozen=True)
class ConversationResponse:
    message: str | None
    kind: ApplicationResultKind = "completed"
    interaction: Optional[ApplicationInteraction] = None
    data: dict[str, Any] = field(default_factory=dict)


class ConversationResponder(Protocol):
    async def generate(self, request: ConversationRequest) -> ConversationResponse: ...
