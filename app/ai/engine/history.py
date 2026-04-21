from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.application.contracts import ApplicationResult
from app.models.conversation_turn import ConversationTurn


DEFAULT_HISTORY_LIMIT = 12


@dataclass(frozen=True)
class RecentClarificationContext:
    message: str
    choices: list[str]
    expected_input: Optional[str]
    kind: Optional[str]


class ConversationHistoryService:
    def __init__(self, default_limit: int = DEFAULT_HISTORY_LIMIT):
        self.default_limit = default_limit

    @staticmethod
    def _session_scope(actor_id: int, channel: str, session_id: str) -> str:
        return session_id or f"{channel}:{actor_id}"

    async def load_recent_turns(
        self,
        actor_id: int,
        channel: str,
        session_id: str,
        limit: int | None = None,
    ) -> list[ConversationTurn]:
        turns = await ConversationTurn.recent_for_session(
            actor_id=actor_id,
            channel=channel,
            session_id=self._session_scope(actor_id, channel, session_id),
            limit=limit or self.default_limit,
        )
        return turns

    async def persist_user_turn(
        self,
        actor_id: int,
        channel: str,
        session_id: str,
        content: str,
    ) -> ConversationTurn:
        return await ConversationTurn.create_turn(
            actor_id=actor_id,
            channel=channel,
            session_id=self._session_scope(actor_id, channel, session_id),
            role="user",
            content=content,
        )

    async def persist_application_turn(
        self,
        actor_id: int,
        channel: str,
        session_id: str,
        response: ApplicationResult,
    ) -> ConversationTurn:
        interaction = response.interaction
        return await ConversationTurn.create_turn(
            actor_id=actor_id,
            channel=channel,
            session_id=self._session_scope(actor_id, channel, session_id),
            role="assistant",
            content=response.message or "",
            kind=response.kind,
            interaction_kind=getattr(interaction, "kind", None),
            choices=list(getattr(interaction, "choices", ()) or ()),
            expected_input=getattr(interaction, "expected_input", None),
        )

    def recent_clarification_context(
        self, turns: list[ConversationTurn]
    ) -> RecentClarificationContext | None:
        for turn in reversed(turns):
            if turn.role == "assistant" and turn.kind == "needs_clarification":
                return RecentClarificationContext(
                    message=turn.content,
                    choices=list(turn.choices),
                    expected_input=turn.expected_input,
                    kind=turn.interaction_kind,
                )
        return None

    def render_turns(self, turns: list[ConversationTurn]) -> str:
        lines: list[str] = []
        for turn in turns:
            prefix = "User" if turn.role == "user" else "Assistant"
            suffix = ""
            if turn.kind == "needs_clarification":
                parts = []
                if turn.choices:
                    parts.append(f"Choices: {', '.join(turn.choices)}")
                if turn.expected_input:
                    parts.append(f"Expected: {turn.expected_input}")
                if parts:
                    suffix = f" ({' | '.join(parts)})"
            lines.append(f"{prefix}: {turn.content}{suffix}")
        return "\n".join(lines)


def build_clarification_hint(context: RecentClarificationContext | None) -> str | None:
    if not context:
        return None
    details = [f"Last clarification: {context.message}"]
    if context.choices:
        details.append(f"Choices: {', '.join(context.choices)}")
    if context.expected_input:
        details.append(f"Expected input: {context.expected_input}")
    return " | ".join(details)
