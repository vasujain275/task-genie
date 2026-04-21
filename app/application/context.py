from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RequestContext:
    actor_id: str
    channel: str
    session_id: str
    timezone: str
    trace_id: str
    locale: Optional[str] = None
