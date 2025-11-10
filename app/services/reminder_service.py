"""
Reminder Service for reminder management operations.
Handles reminder creation, updates, and scheduling.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from beanie import PydanticObjectId

from app.models.reminder import Reminder
from app.models.task import Task
from app.models.user import User
from app.services.nlp_service import NLPService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ReminderService:
    """Service for managing reminders with business logic."""

    def __init__(self):
        self.nlp_service = NLPService()

    # ==================== NLP Integration ====================

    async def process_reminder_from_nlp(
        self, raw_text: str, user: User
    ) -> Optional[Dict[str, Any]]:
        """
        Process raw text input to extract reminder details using NLP.

        Args:
            raw_text: The raw text from user
            user: User object

        Returns:
            Dictionary with parsed reminder details or None if parsing failed
        """
        logger.info(f"Processing reminder from NLP for user {user.telegram_id}")

        try:
            parsed_data = await self.nlp_service.parse_reminder_from_text(
                raw_text, user
            )

            if parsed_data:
                logger.info(
                    f"Successfully parsed reminder: {parsed_data.get('message')}"
                )
                return parsed_data
            else:
                logger.warning("Failed to parse reminder from text")
                return None

        except Exception as e:
            logger.error(f"Error processing reminder from NLP: {e}", exc_info=True)
            return None

    # ==================== CRUD Operations ====================

    async def create_reminder(
        self, user: User, reminder_data: Dict[str, Any]
    ) -> Optional[Reminder]:
        """
        Create a new reminder in the database.

        Args:
            user: User object
            reminder_data: Dictionary with reminder details

        Returns:
            Created Reminder object or None if creation failed
        """
        logger.info(f"Creating reminder for user {user.telegram_id}")

        try:
            # Validate required fields
            if not reminder_data.get("remind_at"):
                logger.error("Missing required field: remind_at")
                return None

            # Get task if task_id is provided
            task = None
            task_id = reminder_data.get("task_id")
            if task_id:
                task = await Task.get(task_id)
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return None

            reminder = Reminder(
                task=task,  # type: ignore
                user=user,  # type: ignore
                remind_at=reminder_data["remind_at"],
                message=reminder_data.get("message"),
                recurrence=reminder_data.get("recurrence"),
            )
            await reminder.insert()
            logger.info(f"Reminder created successfully: {reminder.id}")
            return reminder

        except Exception as e:
            logger.error(f"Error creating reminder: {e}", exc_info=True)
            return None

    async def get_reminder(self, reminder_id: str) -> Optional[Reminder]:
        """
        Get a reminder by ID.

        Args:
            reminder_id: Reminder ID

        Returns:
            Reminder object or None if not found
        """
        try:
            reminder = await Reminder.get(reminder_id)
            if reminder:
                await reminder.fetch_all_links()
            return reminder
        except Exception as e:
            logger.error(f"Error fetching reminder {reminder_id}: {e}", exc_info=True)
            return None

    async def get_user_reminders(
        self, user: User, sent_only: Optional[bool] = None
    ) -> List[Reminder]:
        """
        Get all reminders for a user.

        Args:
            user: User object
            sent_only: If True, only return sent reminders; if False, only pending; if None, return all

        Returns:
            List of Reminder objects
        """
        logger.info(f"Fetching reminders for user {user.telegram_id}")

        try:
            query = Reminder.find(Reminder.user.ref.id == user.id)
            if sent_only is not None:
                query = query.find(Reminder.sent == sent_only)

            reminders = await query.sort("+remind_at").to_list()
            logger.info(f"Found {len(reminders)} reminders for user {user.telegram_id}")
            return reminders

        except Exception as e:
            logger.error(f"Error fetching reminders: {e}", exc_info=True)
            return []

    async def update_reminder(
        self, reminder_id: str, updates: Dict[str, Any]
    ) -> Optional[Reminder]:
        """
        Update an existing reminder.

        Args:
            reminder_id: ID of the reminder to update
            updates: Dictionary of fields to update

        Returns:
            Updated Reminder object or None if update failed
        """
        logger.info(f"Updating reminder {reminder_id}")

        try:
            reminder = await Reminder.get(reminder_id)
            if not reminder:
                logger.warning(f"Reminder {reminder_id} not found for update")
                return None

            # Update timestamp
            updates["updated_at"] = datetime.utcnow()

            # Update fields
            for key, value in updates.items():
                if hasattr(reminder, key):
                    setattr(reminder, key, value)

            await reminder.save()
            logger.info(f"Reminder updated successfully: {reminder_id}")
            return reminder

        except Exception as e:
            logger.error(f"Error updating reminder: {e}", exc_info=True)
            return None

    async def delete_reminder(self, reminder_id: str) -> bool:
        """
        Delete a reminder.

        Args:
            reminder_id: ID of the reminder to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.info(f"Deleting reminder {reminder_id}")

        try:
            reminder = await Reminder.get(reminder_id)
            if not reminder:
                logger.warning(f"Reminder {reminder_id} not found for deletion")
                return False

            await reminder.delete()
            logger.info(f"Reminder deleted successfully: {reminder_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting reminder: {e}", exc_info=True)
            return False

    async def mark_as_sent(self, reminder_id: str) -> Optional[Reminder]:
        """
        Mark a reminder as sent.

        Args:
            reminder_id: ID of the reminder to mark as sent

        Returns:
            Updated Reminder object or None if update failed
        """
        logger.info(f"Marking reminder {reminder_id} as sent")
        reminder = await Reminder.get(reminder_id)
        if reminder:
            return await reminder.mark_as_sent()
        return None

    async def reschedule_reminder(
        self, reminder_id: str, new_time: datetime
    ) -> Optional[Reminder]:
        """
        Reschedule a reminder to a new time.

        Args:
            reminder_id: ID of the reminder to reschedule
            new_time: New reminder time

        Returns:
            Updated Reminder object or None if update failed
        """
        logger.info(f"Rescheduling reminder {reminder_id} to {new_time}")
        reminder = await Reminder.get(reminder_id)
        if reminder:
            return await reminder.reschedule(new_time)
        return None

    # ==================== Advanced Query Operations ====================

    async def get_pending_reminders(self, user: User) -> List[Reminder]:
        """
        Get all pending (unsent) reminders for a user.

        Args:
            user: User object

        Returns:
            List of pending Reminder objects
        """
        logger.info(f"Fetching pending reminders for user {user.telegram_id}")

        try:
            reminders = await Reminder.get_pending_reminders(user.id)  # type: ignore
            logger.info(f"Found {len(reminders)} pending reminders")
            return reminders
        except Exception as e:
            logger.error(f"Error fetching pending reminders: {e}", exc_info=True)
            return []

    async def get_due_reminders(
        self, before_time: Optional[datetime] = None
    ) -> List[Reminder]:
        """
        Get all reminders that are due (remind_at <= current time) and not sent.

        Args:
            before_time: Optional cutoff time, defaults to now

        Returns:
            List of due Reminder objects
        """
        logger.info("Fetching due reminders")

        try:
            reminders = await Reminder.get_due_reminders(before_time)
            logger.info(f"Found {len(reminders)} due reminders")
            return reminders
        except Exception as e:
            logger.error(f"Error fetching due reminders: {e}", exc_info=True)
            return []

    async def get_upcoming_reminders(
        self, user: User, limit: int = 5
    ) -> List[Reminder]:
        """
        Get upcoming reminders for a user.

        Args:
            user: User object
            limit: Maximum number of reminders to return

        Returns:
            List of upcoming Reminder objects
        """
        logger.info(f"Fetching upcoming reminders for user {user.telegram_id}")

        try:
            reminders = await Reminder.get_upcoming_reminders(user.id, limit)  # type: ignore
            logger.info(f"Found {len(reminders)} upcoming reminders")
            return reminders
        except Exception as e:
            logger.error(f"Error fetching upcoming reminders: {e}", exc_info=True)
            return []

    async def get_reminders_by_task(self, task_id: str) -> List[Reminder]:
        """
        Get all reminders for a specific task.

        Args:
            task_id: Task ID

        Returns:
            List of Reminder objects
        """
        logger.info(f"Fetching reminders for task {task_id}")

        try:
            task = await Task.get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return []

            reminders = await Reminder.get_reminders_by_task(task.id)  # type: ignore
            logger.info(f"Found {len(reminders)} reminders for task")
            return reminders
        except Exception as e:
            logger.error(f"Error fetching reminders by task: {e}", exc_info=True)
            return []

    async def get_reminders_by_date_range(
        self,
        user: User,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Reminder]:
        """
        Get reminders within a date range.

        Args:
            user: User object
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of Reminder objects within the date range
        """
        logger.info(f"Fetching reminders for user {user.telegram_id} from {start_date} to {end_date}")

        try:
            reminders = await Reminder.get_reminders_by_date_range(
                user.id, start_date, end_date  # type: ignore
            )
            logger.info(f"Found {len(reminders)} reminders in date range")
            return reminders
        except Exception as e:
            logger.error(f"Error fetching reminders by date range: {e}", exc_info=True)
            return []

    async def get_reminder_statistics(self, user: User) -> Dict[str, Any]:
        """
        Get reminder statistics for a user.

        Args:
            user: User object

        Returns:
            Dictionary with reminder statistics
        """
        logger.info(f"Fetching reminder statistics for user {user.telegram_id}")

        try:
            stats = await Reminder.get_reminder_statistics(user.id)  # type: ignore
            return stats
        except Exception as e:
            logger.error(f"Error fetching reminder statistics: {e}", exc_info=True)
            return {"total": 0, "by_status": []}

    # ==================== Scheduling Operations ====================

    async def schedule_reminder(self, reminder: Reminder) -> bool:
        """
        Schedule a reminder for delivery at the specified time.
        This is a placeholder for actual scheduling logic (APScheduler, Celery, etc.)

        Args:
            reminder: Reminder object to schedule

        Returns:
            True if scheduling was successful, False otherwise
        """
        logger.info(f"Scheduling reminder {reminder.id}")

        try:
            # TODO: Implement actual reminder scheduling logic
            # This could use APScheduler, Celery, or another task queue
            # Example:
            # scheduler.add_job(
            #     send_reminder,
            #     trigger='date',
            #     run_date=reminder.remind_at,
            #     args=[str(reminder.id)]
            # )

            logger.info(f"Reminder {reminder.id} scheduled for {reminder.remind_at}")
            return True

        except Exception as e:
            logger.error(f"Error scheduling reminder: {e}", exc_info=True)
            return False

    async def get_today_reminders(self, user: User) -> List[Reminder]:
        """
        Get reminders for today.

        Args:
            user: User object

        Returns:
            List of reminders for today
        """
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return await self.get_reminders_by_date_range(user, start_of_day, end_of_day)

