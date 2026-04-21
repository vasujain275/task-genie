from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def convert_utc_to_user_timezone(
    dt: datetime | None, user_timezone: str
) -> datetime | None:
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    try:
        return dt.astimezone(ZoneInfo(user_timezone))
    except (ZoneInfoNotFoundError, ValueError, Exception):
        logger.warning("Invalid timezone '%s'; falling back to UTC", user_timezone)
        return dt.astimezone(ZoneInfo("UTC"))
