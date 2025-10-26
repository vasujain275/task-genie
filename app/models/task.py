from beanie import Document
from typing import Optional, Literal
from pydantic import Field
from datetime import datetime

class Task(Document):
    user_id: str
    title: str
    description: Optional[str]
    task_datetime: datetime
    recurrence: Optional[str]
    status: Literal["pending","done"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
