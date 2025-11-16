# Quick Reference Guide - Natural Language Task Creation

## 🎯 User Flow

### 1. First Time Setup
```
User: /start

Bot: Shows welcome message
     - Configure timezone
     - Configure OpenAI API key

User: Configures settings

Bot: "Ready to help! Just tell me what you need to do..."
     Sets state to ConversationMode.active
```

### 2. Creating a Task
```
User: "Call mom tomorrow evening"

Bot: [Shows typing indicator]
     Parses with OpenAI
     Changes state to TaskCreationStates.confirming_task

     "Should I add task **Call Mom** for tomorrow at 6:00 PM?

      🔔 I'll remind you at 5:45 PM.

      Reply **Yes** to confirm or tell me what to change."

      [✅ Yes, create it] [❌ Cancel]

User: Clicks "Yes" (or types "yes")

Bot: Creates task and reminder in MongoDB
     Changes state back to ConversationMode.active

     "✅ Task created successfully!

      📋 **Call Mom**
      📅 Due: tomorrow at 6:00 PM

      🔔 Reminder set for tomorrow at 5:45 PM"
```

### 3. Cancelling
```
User: "Team meeting tomorrow"

Bot: Shows confirmation...

User: Clicks "Cancel" (or types "no")

Bot: "Task creation cancelled. What else can I help you with?"
     Changes state to ConversationMode.active
```

### 4. Modifying
```
User: "Buy groceries today"

Bot: Shows confirmation...

User: "No, make it tomorrow at 5pm"

Bot: "Got it! Let me parse that as a new task..."
     Re-processes as new input
     Shows new confirmation
```

## 🔑 Key Components

### States (app/bot/states.py)
```python
ConversationMode.active              # Waiting for NL input
TaskCreationStates.confirming_task   # Asking for confirmation
TaskCreationStates.editing_task_details  # Editing (future)
TaskCreationStates.processing        # Creating task (future)
```

### Handlers (app/bot/handlers/conversation.py)
```python
handle_natural_language_message()    # Entry point for NL messages
handle_task_confirmation()           # Handles yes/no responses
callback_confirm_task()              # Inline button: Yes
callback_cancel_task()               # Inline button: Cancel
```

### NLP Service (app/ai/nlp_service.py)
```python
nlp_service.process_message()        # Parse NL → task data
nlp_service.confirm_task()           # Create confirmed task
```

### Graph Nodes (app/ai/graph/task_flow.py)
```python
parse_input_node()                   # Parse NL with OpenAI
create_task_node()                   # Save to MongoDB
```

## 📋 DateTime Parsing Rules

### Time Keywords
- `morning` → 9:00 AM
- `afternoon` → 2:00 PM
- `evening` → 6:00 PM
- `tonight` → 8:00 PM

### Relative Dates
- `today` → Current date
- `tomorrow` → Next day
- `next Monday` → Next occurrence of Monday
- `next week` → 7 days from now

### Default Behaviors
- No time specified → 9:00 AM
- No reminder specified → 15 minutes before task
- All times in user's timezone

## 🗄️ Database Models

### Task (app/models/task.py)
```python
{
    "user": Link[User],
    "title": str,
    "description": Optional[str],
    "task_datetime": datetime,
    "priority": "low" | "medium" | "high",
    "tags": List[str],
    "recurrence": Optional[str],
    "status": "pending" | "done"
}
```

### Reminder (app/models/reminder.py)
```python
{
    "task": Link[Task],
    "user": Link[User],
    "remind_at": datetime,
    "message": Optional[str],
    "sent": bool,
    "recurrence": Optional[str]
}
```

## 🧵 Conversation Threading

### Thread ID Format
```python
# Daily isolation
thread_id = f"user_{user_id}_date_{YYYY-MM-DD}"

# Example
"user_123456_date_2025-11-16"  # Today
"user_123456_date_2025-11-17"  # Tomorrow (new conversation)
```

### Checkpointing
- Stored in Redis
- TTL: 24 hours
- Automatic cleanup of 7+ day old conversations
- Key format: `checkpoint:user_{id}_date_{date}`

## 🎨 Response Format

### Confirmation Message
```markdown
Should I add task **{title}** for {datetime}?

📝 Details: {description}  # If present

🔔 I'll remind you at {reminder_time}.

Reply **Yes** to confirm or tell me what to change.
```

### Success Message
```markdown
✅ Task created successfully!

📋 **{title}**
📅 Due: {datetime}
📝 {description}  # If present

🔔 Reminder set for {reminder_time}  # If present
```

### Error Message
```markdown
I couldn't understand that task. Could you rephrase it?

For example: 'Call mom tomorrow at 6pm' or 'Team meeting next Monday at 10am'
```

## 🔧 Debugging

### Check Conversation State
```python
# In Redis
redis-cli
> GET checkpoint:user_123456_date_2025-11-16
```

### Check FSM State
```python
# In handler
current_state = await state.get_state()
print(f"Current state: {current_state}")
```

### Check Parsed Data
```python
# In handler
data = await state.get_data()
print(f"Task data: {data.get('task_data')}")
print(f"Reminder data: {data.get('reminder_data')}")
```

## 🐛 Common Issues

### "OpenAI API key not configured"
→ User needs to use `/settings` and configure API key

### "Could not understand that task"
→ Message was too vague or LLM couldn't parse
→ Show examples to user

### Task created but no reminder
→ Check if `has_reminder` flag is set
→ Check reminder_data in graph state

### Wrong timezone
→ User needs to update timezone in `/settings`
→ Check `user.timezone` in database

## 📊 Testing Commands

```bash
# Start bot
python -m app.main

# Check Redis
redis-cli KEYS "checkpoint:*"
redis-cli GET "checkpoint:user_123456_date_2025-11-16"

# Check MongoDB
mongo
> use task_genie
> db.tasks.find({})
> db.reminders.find({})
```

## 🎯 Next Steps

1. Install dependencies: `uv pip install -e .`
2. Start Redis: `redis-server`
3. Configure bot token in `.env`
4. Start bot: `python -m app.main`
5. Test with `/start` and natural language inputs
6. Monitor logs for any issues
7. Check MongoDB for created tasks/reminders

## 💡 Tips

- Use descriptive task messages for better parsing
- Include time when possible ("at 6pm" vs "evening")
- Be specific with dates ("next Monday" vs "soon")
- Test confirmation flow thoroughly
- Monitor Redis memory usage
- Set up log rotation for production
