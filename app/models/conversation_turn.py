from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from beanie import Document
from pydantic import Field


ConversationTurnRole = Literal["user", "assistant"]
CONVERSATION_TURN_RETENTION_DAYS = 14


class ConversationTurn(Document):
    actor_id: int
    channel: str
    session_id: str
    role: ConversationTurnRole
    content: str
    kind: Optional[str] = None
    interaction_kind: Optional[str] = None
    choices: list[str] = Field(default_factory=list)
    expected_input: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "conversation_turns"
        use_state_management = True
        retention_days = CONVERSATION_TURN_RETENTION_DAYS
        indexes = [
            "actor_id",
            "channel",
            "session_id",
            {
                "keys": [("created_at", 1)],
                "expireAfterSeconds": CONVERSATION_TURN_RETENTION_DAYS * 24 * 60 * 60,
                "name": "conversation_turns_created_at_ttl",
            },
        ]

    @classmethod
    async def create_turn(cls, **data) -> "ConversationTurn":
        turn = cls(**data)
        await turn.insert()
        return turn

    @classmethod
    async def recent_for_session(
        cls,
        actor_id: int,
        channel: str,
        session_id: str,
        limit: int = 12,
    ) -> list["ConversationTurn"]:
        query = cls.find(
            cls.actor_id == actor_id,
            cls.channel == channel,
            cls.session_id == session_id,
        ).sort("-created_at")
        turns = await query.limit(limit).to_list()
        return list(reversed(turns))
