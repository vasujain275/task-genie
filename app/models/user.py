from beanie import Document
from typing import Optional
from datetime import datetime
from pydantic import Field

class User(Document):
    telegram_id: int
    name: str
    gemini_key: Optional[str]
    openAI_key: Optional[str]
    default_ai: str = "gemini"
    timezone: str = "Asia/Kolkata"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
