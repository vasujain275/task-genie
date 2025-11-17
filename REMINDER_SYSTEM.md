# Reminder System Architecture

## Overview

The reminder system uses **APScheduler** to run a background job every minute that queries MongoDB for due reminders and sends them via Telegram.

## Why This Approach?

### ✅ Advantages

1. **Simple & Reliable**
   - No additional infrastructure needed (no queue system)
   - MongoDB already indexed on `remind_at` and `sent` fields
   - Single source of truth (MongoDB)

2. **Efficient**
   - Queries only reminders in current minute window
   - Uses MongoDB indexes for fast lookups
   - Processes reminders in parallel

3. **Integration**
   - Cleanly integrates with FastAPI lifespan
   - Automatic startup/shutdown
   - No external dependencies beyond APScheduler

4. **Scalability**
   - Query time: O(log n) due to indexes
   - Typical reminder volume: low (< 100 per minute)
   - Can handle thousands of users easily

### ❌ Why NOT Redis Queue?

1. **Complexity**: Requires maintaining two systems (MongoDB + Redis queue)
2. **Sync Issues**: Risk of queue and DB being out of sync
3. **Overhead**: Need to populate queue from DB anyway
4. **Unnecessary**: MongoDB is fast enough for this use case

## Architecture Flow

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI App Startup                    │
│                                                          │
│  1. Initialize MongoDB                                   │
│  2. Setup Bot & Dispatcher                               │
│  3. Start Reminder Scheduler ← NEW                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              APScheduler (Background Job)                │
│                                                          │
│  Cron: Every minute at :00 seconds                       │
│  Job: process_due_reminders()                            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   MongoDB Query                          │
│                                                          │
│  Find reminders where:                                   │
│    - sent = False                                        │
│    - remind_at >= current_minute_start                   │
│    - remind_at < next_minute_start                       │
│                                                          │
│  Uses index: (remind_at, sent)                           │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Process Each Reminder                       │
│                                                          │
│  For each reminder:                                      │
│    1. Fetch linked Task & User                           │
│    2. Format notification message                        │
│    3. Send via bot.send_message()                        │
│    4. Mark as sent in DB                                 │
│    5. Handle recurrence (TODO)                           │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Telegram Notification                   │
│                                                          │
│  User receives:                                          │
│    🔔 Reminder                                           │
│    📋 Task: [title]                                      │
│    ⏰ Scheduled: [datetime]                              │
│    💬 Note: [message]                                    │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. Reminder Model (`app/models/reminder.py`)

Already has the necessary fields:
- `remind_at`: DateTime when reminder should be sent
- `sent`: Boolean flag (indexed for fast queries)
- `recurrence`: Optional recurring pattern
- Indexes on `remind_at` and `sent` for efficient queries

### 2. Scheduler Service (`app/services/reminder_scheduler.py`)

**Key Functions:**

- `start_reminder_scheduler()`: Initializes APScheduler on app startup
- `stop_reminder_scheduler()`: Gracefully shuts down on app shutdown
- `process_due_reminders()`: Main job that runs every minute
- `send_reminder_notification(reminder)`: Sends individual notification

**Configuration:**

```python
scheduler.add_job(
    process_due_reminders,
    trigger=CronTrigger(second=0),  # Run at :00 of every minute
    id="process_due_reminders",
    max_instances=1,  # Prevent overlapping executions
)
```

### 3. Integration (`app/main.py`)

The scheduler starts/stops with the FastAPI app lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db(client)
    start_reminder_scheduler()  # ← Start scheduler

    yield  # App runs

    # Shutdown
    stop_reminder_scheduler()  # ← Stop scheduler
```

## Performance Considerations

### Query Optimization

**Time Window Strategy:**
```python
# If current time is 14:35:30
minute_start = 14:35:00
minute_end = 14:36:00

# Query only reminders in this 1-minute window
reminders = await Reminder.find({
    "sent": False,
    "remind_at": {"$gte": minute_start, "$lt": minute_end}
}).to_list()
```

**Why 1-minute window?**
- Reduces query result size
- Ensures timely delivery
- Prevents duplicate sends
- Easy retry on failure (next minute)

### MongoDB Indexes

Already defined in `Reminder.Settings`:
```python
indexes = [
    "user",
    "task",
    "remind_at",  # ← Critical for scheduler
    "sent",        # ← Critical for scheduler
]
```

**Compound Index Recommendation:**
Add a compound index for even better performance:
```python
indexes = [
    "user",
    "task",
    [("sent", 1), ("remind_at", 1)],  # Compound index
]
```

### Scalability

**Current Load:**
- Runs every 60 seconds
- Typical query: < 100 reminders per minute
- Query time: < 50ms with indexes
- Send time: ~100ms per reminder
- Total time: ~10 seconds for 100 reminders

**At Scale (10,000 users):**
- Assume 10% get 1 reminder/hour = 1000 reminders/hour
- ~17 reminders per minute
- Query + send: ~2 seconds
- Well within 60-second job window

**If needed to scale further:**
1. Batch send messages (aiogram supports this)
2. Use multiple workers
3. Consider sharding by time zones

## Error Handling

### Retry Logic

If a reminder fails to send, it remains `sent=False` and will be retried next minute:

```python
sent_successfully = await send_reminder_notification(reminder)

if sent_successfully:
    await reminder.mark_as_sent()
else:
    # Don't mark as sent - will retry next minute
    logger.warning(f"Reminder {reminder.id} failed, will retry")
```

### Overlapping Prevention

APScheduler prevents overlapping executions:
```python
max_instances=1  # Only 1 instance runs at a time
```

If a job takes > 60 seconds, the next scheduled run will skip.

## Recurring Reminders (TODO)

Currently marked as TODO. Implementation strategy:

### Option 1: Create New Reminder
```python
if reminder.recurrence:
    # Calculate next occurrence
    next_time = calculate_next_occurrence(
        reminder.remind_at,
        reminder.recurrence
    )

    # Create new reminder
    new_reminder = Reminder(
        task=reminder.task,
        user=reminder.user,
        remind_at=next_time,
        recurrence=reminder.recurrence,
        message=reminder.message,
    )
    await new_reminder.insert()

    # Mark current as sent
    await reminder.mark_as_sent()
```

### Option 2: Update Existing Reminder
```python
if reminder.recurrence:
    # Calculate next occurrence
    next_time = calculate_next_occurrence(
        reminder.remind_at,
        reminder.recurrence
    )

    # Reschedule same reminder
    await reminder.reschedule(next_time)
```

**Recommendation:** Option 1 (create new) for better audit trail.

## Installation

Install APScheduler:

```bash
pip install apscheduler
```

Or use the updated `pyproject.toml`:

```bash
uv sync
```

## Testing

### Test the Scheduler

1. **Create a test reminder:**
```python
from datetime import datetime, timedelta
from app.models.reminder import Reminder

# Create reminder for 2 minutes from now
remind_time = datetime.utcnow() + timedelta(minutes=2)

reminder = await Reminder.create_for_task(
    task_id="your_task_id",
    remind_at=remind_time,
    message="Test reminder!"
)
```

2. **Start the app:**
```bash
uvicorn app.main:app --reload
```

3. **Check logs:**
```
✅ Reminder scheduler started successfully
📅 Scheduled job: process_due_reminders (runs every minute)
⏰ Checking reminders due between 14:35:00 and 14:36:00
📬 Found 1 reminder(s) to process
✅ Reminder sent to user 123456789 for task 'Test Task'
```

### Manual Test Query

Check what reminders are due:
```python
from datetime import datetime, timedelta

now = datetime.utcnow()
minute_start = now.replace(second=0, microsecond=0)
minute_end = minute_start + timedelta(minutes=1)

due_reminders = await Reminder.find({
    "sent": False,
    "remind_at": {
        "$gte": minute_start,
        "$lt": minute_end
    }
}).to_list()

print(f"Found {len(due_reminders)} due reminders")
```

## Monitoring

### Key Metrics to Monitor

1. **Job execution time**: Should be < 60 seconds
2. **Failed sends**: Track in logs
3. **Reminder backlog**: Query for overdue unsent reminders
4. **Query performance**: MongoDB slow query log

### Health Check

Add a health endpoint for the scheduler:

```python
@app.get("/health/scheduler")
async def scheduler_health():
    from app.services.reminder_scheduler import scheduler

    if scheduler and scheduler.running:
        jobs = scheduler.get_jobs()
        return {
            "status": "running",
            "jobs": len(jobs),
            "next_run": str(jobs[0].next_run_time) if jobs else None
        }
    return {"status": "stopped"}
```

## Alternative Approaches Considered

### ❌ Celery Beat
- **Pros**: Mature, distributed
- **Cons**: Heavy, requires broker (Redis/RabbitMQ), overkill for this use case

### ❌ Redis Queue with Workers
- **Pros**: True async, distributed
- **Cons**: Complex, state sync issues, requires worker processes

### ❌ Cron + Script
- **Pros**: Simple, OS-level
- **Cons**: Separate process, harder to integrate, no access to app state

### ✅ APScheduler (Chosen)
- **Pros**: Lightweight, integrated, async support, perfect for this scale
- **Cons**: Single process (fine for most use cases)

## Future Enhancements

1. **Recurring reminders**: Implement full recurrence logic
2. **Timezone handling**: Send at user's local time
3. **Batch sending**: Group notifications for efficiency
4. **Smart notifications**: Don't send if task already completed
5. **Snooze feature**: Allow users to delay reminders
6. **Delivery status**: Track if message was read
7. **Priority queue**: Send high-priority reminders first

## Summary

The reminder system is:
- ✅ **Simple**: Just APScheduler + MongoDB
- ✅ **Reliable**: Single source of truth
- ✅ **Efficient**: Indexed queries, 1-minute windows
- ✅ **Scalable**: Can handle thousands of users
- ✅ **Integrated**: Clean startup/shutdown with FastAPI

No need for Redis queues or complex infrastructure!
