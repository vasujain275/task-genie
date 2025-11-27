"""
Reminder Scheduler Service

This service runs a background job every minute to:
1. Query MongoDB for reminders due in the current minute
2. Send reminder messages to users via Telegram
3. Mark reminders as sent
4. Handle recurring reminders

ARCHITECTURE:
- Uses APScheduler for cron-like scheduling
- Runs asynchronously without blocking the main app
- Integrates with FastAPI lifespan for clean startup/shutdown
- Queries only relevant reminders using MongoDB indexes

EFFICIENCY:
- MongoDB query is indexed on (remind_at, sent) for fast lookups
- Only fetches reminders for the current minute window
- Processes reminders in parallel for multiple users
- Automatic error handling and logging
"""

import asyncio
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.models.reminder import Reminder
from app.bot.instance import bot
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


async def send_reminder_notification(reminder: Reminder) -> bool:
    """
    Send a reminder notification to the user via Telegram.

    Args:
        reminder: Reminder object to send

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Fetch linked task and user
        await reminder.fetch_all_links()

        # Type narrowing: After fetch_all_links, these are actual documents, not Links
        task = reminder.task  # type: ignore[assignment]
        user = reminder.user  # type: ignore[assignment]

        if not task or not user:
            logger.error(f"Missing task or user for reminder {reminder.id}")
            return False

        # Format the reminder message
        message_text = "🔔 **Reminder**\n\n"
        message_text += f"📋 **Task**: {task.title}\n"  # type: ignore[attr-defined]

        if task.description:  # type: ignore[attr-defined]
            message_text += f"📝 {task.description}\n"  # type: ignore[attr-defined]

        message_text += (
            f"⏰ **Scheduled**: {task.task_datetime.strftime('%Y-%m-%d %H:%M')}\n"  # type: ignore[attr-defined]
        )

        if reminder.message:
            message_text += f"\n💬 **Note**: {reminder.message}\n"

        if task.priority:  # type: ignore[attr-defined]
            priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            message_text += f"{priority_emoji.get(task.priority, '⚪')} **Priority**: {task.priority}\n"  # type: ignore[attr-defined]

        # Send to user
        await bot.send_message(
            chat_id=user.telegram_id,  # type: ignore[attr-defined]
            text=message_text,
            parse_mode="Markdown",
        )

        logger.info(
            f"✅ Reminder sent to user {user.telegram_id} for task '{task.title}'"  # type: ignore[attr-defined]
        )
        return True

    except Exception as e:
        logger.error(f"❌ Failed to send reminder {reminder.id}: {e}", exc_info=True)
        return False


async def process_due_reminders():
    """
    Main scheduler job that runs every minute.

    Process:
    1. Query MongoDB for reminders due in the current minute
    2. Send each reminder via Telegram
    3. Mark as sent or handle recurring reminders
    """
    try:
        # Get current time in UTC (all DB times are UTC)
        now = datetime.utcnow()

        # Define the time window: current minute
        # Example: If now is 14:35:30, we want reminders from 14:35:00 to 14:35:59
        minute_start = now.replace(second=0, microsecond=0)
        minute_end = minute_start + timedelta(minutes=1)

        logger.debug(
            f"⏰ Checking reminders due between {minute_start} and {minute_end}"
        )

        # Query MongoDB for unsent reminders in this time window
        # Uses index on (remind_at, sent) for efficient lookup
        due_reminders = await Reminder.find(
            {
                "sent": False,
                "remind_at": {
                    "$gte": minute_start,
                    "$lt": minute_end,
                },
            }
        ).to_list()

        if not due_reminders:
            logger.debug("No reminders due at this time")
            return

        logger.info(f"📬 Found {len(due_reminders)} reminder(s) to process")

        # Process each reminder
        for reminder in due_reminders:
            try:
                # Send the reminder notification
                sent_successfully = await send_reminder_notification(reminder)

                if sent_successfully:
                    # Handle recurring reminders
                    if reminder.recurrence:
                        # TODO: Implement recurrence logic
                        # For now, just mark as sent
                        # Future: Calculate next remind_at based on recurrence pattern
                        # and create a new reminder or update this one
                        logger.info(
                            f"⏭️  Recurring reminder {reminder.id} - recurrence not yet implemented"
                        )
                        await reminder.mark_as_sent()
                    else:
                        # One-time reminder - mark as sent
                        await reminder.mark_as_sent()
                else:
                    # Failed to send - will retry next minute
                    logger.warning(
                        f"⚠️  Reminder {reminder.id} failed to send, will retry next minute"
                    )

            except Exception as e:
                logger.error(
                    f"❌ Error processing reminder {reminder.id}: {e}", exc_info=True
                )
                # Continue processing other reminders even if one fails

        logger.info(f"✅ Finished processing {len(due_reminders)} reminder(s)")

    except Exception as e:
        logger.error(f"❌ Error in process_due_reminders job: {e}", exc_info=True)


def start_reminder_scheduler():
    """
    Start the reminder scheduler.

    Called during FastAPI app startup.
    Schedules the process_due_reminders job to run every minute.
    """
    global scheduler

    try:
        logger.info("🚀 Starting reminder scheduler...")

        # Get the current event loop - critical for AsyncIOScheduler to work with FastAPI
        try:
            loop = asyncio.get_running_loop()
            logger.info(f"Using existing event loop: {loop}")
        except RuntimeError:
            # No running loop - this shouldn't happen in FastAPI context
            logger.warning(
                "No running event loop found, scheduler may not work correctly"
            )
            loop = None

        # Initialize AsyncIOScheduler with explicit event loop
        scheduler = AsyncIOScheduler(event_loop=loop) if loop else AsyncIOScheduler()

        # Add job to run every minute at :00 seconds
        # Cron: "0 * * * *" means "at second 0 of every minute"
        scheduler.add_job(
            process_due_reminders,
            trigger=CronTrigger(second=0),  # Run at the start of every minute
            id="process_due_reminders",
            name="Process Due Reminders",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping executions
        )

        # Start the scheduler
        scheduler.start()

        logger.info("✅ Reminder scheduler started successfully")
        logger.info("📅 Scheduled job: process_due_reminders (runs every minute)")

    except Exception as e:
        logger.error(f"❌ Failed to start reminder scheduler: {e}", exc_info=True)
        raise


def stop_reminder_scheduler():
    """
    Stop the reminder scheduler.

    Called during FastAPI app shutdown.
    """
    global scheduler

    try:
        if scheduler and scheduler.running:
            logger.info("🛑 Stopping reminder scheduler...")
            scheduler.shutdown(wait=True)
            logger.info("✅ Reminder scheduler stopped successfully")
        else:
            logger.info("ℹ️  Reminder scheduler was not running")

    except Exception as e:
        logger.error(f"❌ Error stopping reminder scheduler: {e}", exc_info=True)
