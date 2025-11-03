from pydantic import BaseModel

# ============= API MODELS =============

class SettingsUpdate(BaseModel):
    init_data: str  # The signed data from Telegram
    timezone: str
    default_ai: str
    api_key: str
