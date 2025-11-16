# Architecture Diagram - Task Genie NLP System

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Telegram User                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ "Call mom tomorrow evening"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Aiogram Dispatcher                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FSM State: ConversationMode.active                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│           conversation.py: handle_natural_language_message()     │
│  • Check user exists                                             │
│  • Check OpenAI key configured                                   │
│  • Show typing indicator                                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NLPService.process_message()                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Generate conversation_id: user_123456_date_2025-11-16│  │
│  │  2. Initialize GraphState                                 │  │
│  │  3. Configure checkpointer with thread_id                 │  │
│  │  4. Run LangGraph workflow                                │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LangGraph Workflow                           │
│                                                                  │
│  ┌────────────────────┐                                         │
│  │  parse_input_node  │                                         │
│  └──────────┬─────────┘                                         │
│             │                                                    │
│             │ Call OpenAI GPT-4                                 │
│             │                                                    │
│             ▼                                                    │
│  ┌─────────────────────────────────────────┐                   │
│  │  Parse JSON Response:                    │                   │
│  │  {                                       │                   │
│  │    "task_title": "Call Mom",             │                   │
│  │    "task_datetime": "2025-11-17T18:00",  │                   │
│  │    "reminder_time": "2025-11-17T17:45",  │                   │
│  │    "priority": "medium"                  │                   │
│  │  }                                       │                   │
│  └─────────────────────────────────────────┘                   │
│             │                                                    │
│             ▼                                                    │
│  ┌────────────────────┐                                         │
│  │  Generate          │                                         │
│  │  Confirmation      │                                         │
│  │  Message           │                                         │
│  └──────────┬─────────┘                                         │
│             │                                                    │
│             │ needs_confirmation = True                         │
│             │                                                    │
│             ▼                                                    │
│  ┌────────────────────┐                                         │
│  │    WAIT            │  (Return to handler)                    │
│  └────────────────────┘                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Save state to Redis
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Redis Checkpointer                             │
│  Key: checkpoint:user_123456_date_2025-11-16                    │
│  Value: {                                                        │
│    "task_data": {...},                                          │
│    "reminder_data": {...},                                      │
│    "needs_confirmation": true,                                  │
│    "confirmation_message": "Should I add task..."               │
│  }                                                               │
│  TTL: 24 hours                                                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Back to Handler                                │
│  • Change FSM state to TaskCreationStates.confirming_task       │
│  • Send confirmation message with inline buttons                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Telegram User                            │
│                                                                  │
│  Message: "Should I add task **Call Mom** for tomorrow at       │
│            6:00 PM? I'll remind you at 5:45 PM."                │
│                                                                  │
│  Buttons: [✅ Yes, create it] [❌ Cancel]                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ User clicks "Yes"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│         conversation.py: callback_confirm_task()                 │
│  OR handle_task_confirmation() if typed "yes"                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  NLPService.confirm_task()                       │
│  1. Get checkpoint from Redis                                    │
│  2. Extract task_data and reminder_data                          │
│  3. Call create_task_node()                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    create_task_node()                            │
│                                                                  │
│  1. Get user from DB                                             │
│  2. Create Task in MongoDB                                       │
│  3. Create Reminder in MongoDB                                   │
│  4. Generate success message                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MongoDB                                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ tasks collection:                                         │  │
│  │ {                                                         │  │
│  │   "_id": ObjectId("..."),                                │  │
│  │   "user": Link(User),                                    │  │
│  │   "title": "Call Mom",                                   │  │
│  │   "task_datetime": ISODate("2025-11-17T18:00:00Z"),     │  │
│  │   "priority": "medium",                                  │  │
│  │   "status": "pending"                                    │  │
│  │ }                                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ reminders collection:                                     │  │
│  │ {                                                         │  │
│  │   "_id": ObjectId("..."),                                │  │
│  │   "task": Link(Task),                                    │  │
│  │   "user": Link(User),                                    │  │
│  │   "remind_at": ISODate("2025-11-17T17:45:00Z"),         │  │
│  │   "sent": false                                          │  │
│  │ }                                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Back to Handler                                │
│  • Change FSM state to ConversationMode.active                   │
│  • Send success message                                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Telegram User                            │
│                                                                  │
│  Message: "✅ Task created successfully!                         │
│            📋 **Call Mom**                                       │
│            📅 Due: tomorrow at 6:00 PM                           │
│            🔔 Reminder set for tomorrow at 5:45 PM"             │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### GraphState Journey

```python
# 1. Initial State (parse_input_node)
{
    "user_message": "Call mom tomorrow evening",
    "user_id": 123456,
    "user_timezone": "America/New_York",
    "conversation_id": "user_123456_date_2025-11-16",
    "task_data": None,
    "reminder_data": None,
    "needs_confirmation": False
}

# 2. After Parsing
{
    "user_message": "Call mom tomorrow evening",
    "user_id": 123456,
    "user_timezone": "America/New_York",
    "conversation_id": "user_123456_date_2025-11-16",
    "task_data": {
        "title": "Call Mom",
        "task_datetime": datetime(2025, 11, 17, 18, 0),
        "priority": "medium"
    },
    "reminder_data": {
        "remind_at": datetime(2025, 11, 17, 17, 45)
    },
    "needs_confirmation": True,
    "confirmation_message": "Should I add task **Call Mom**..."
}

# 3. After Confirmation (create_task_node)
{
    ...
    "user_confirmed": True,
    "task_created": True,
    "reminder_created": True,
    "response_message": "✅ Task created successfully!..."
}
```

## Component Interaction

```
┌─────────────────┐
│   User Input    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│   FSM States    │────▶│  Aiogram Router  │
│  (states.py)    │     │  (conversation)  │
└─────────────────┘     └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │   NLP Service    │
                        │ (nlp_service.py) │
                        └────────┬─────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌──────────┐  ┌──────────┐  ┌──────────┐
            │  Graph   │  │  Tools   │  │Checkpoint│
            │ (flow)   │  │ (parser) │  │ (Redis)  │
            └──────────┘  └──────────┘  └──────────┘
                    │            │
                    └────────────┼────────────┐
                                 ▼            ▼
                        ┌──────────────┐  ┌──────────┐
                        │  OpenAI API  │  │ MongoDB  │
                        └──────────────┘  └──────────┘
```

## File Dependencies

```
app/bot/handlers/conversation.py
├── app/models/user.py
├── app/bot/states.py
├── app/bot/keyboards/inline.py
└── app/ai/nlp_service.py
    ├── app/ai/graph/task_flow.py
    │   ├── app/ai/state.py
    │   ├── app/ai/tools/parser.py
    │   │   ├── app/ai/prompts/system.py
    │   │   └── langchain_openai (external)
    │   ├── app/models/task.py
    │   └── app/models/reminder.py
    └── app/ai/checkpointer.py
        └── redis (external)
```

## State Transitions

```
┌────────────────────────┐
│ User starts bot        │
│ /start command         │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ ConversationMode.active│◄─────────────┐
└──────────┬─────────────┘              │
           │                             │
           │ User sends NL message       │
           │                             │
           ▼                             │
┌────────────────────────┐              │
│ Processing...          │              │
└──────────┬─────────────┘              │
           │                             │
           │ Task parsed                 │
           │                             │
           ▼                             │
┌──────────────────────────┐            │
│ TaskCreationStates       │            │
│ .confirming_task         │            │
└──────────┬───────────────┘            │
           │                             │
           │ User confirms/cancels       │
           │                             │
           └─────────────────────────────┘
```

## Error Handling Flow

```
User Input
    │
    ▼
┌─────────────────────┐
│ Check User Exists   │──No──▶ "User not found"
└──────────┬──────────┘
          Yes
           │
           ▼
┌─────────────────────┐
│ Check API Key       │──No──▶ "Configure OpenAI key"
└──────────┬──────────┘
          Yes
           │
           ▼
┌─────────────────────┐
│ Parse with LLM      │──Error──▶ "Could not understand"
└──────────┬──────────┘
      Success
           │
           ▼
┌─────────────────────┐
│ Generate            │──No data──▶ "Please rephrase"
│ Confirmation        │
└──────────┬──────────┘
      Success
           │
           ▼
┌─────────────────────┐
│ Create in DB        │──Error──▶ "Failed to create"
└──────────┬──────────┘
      Success
           │
           ▼
     "✅ Success!"
```

## Scalability Considerations

1. **Redis Checkpointing**
   - Horizontal scaling possible
   - Each user's conversation is isolated
   - TTL prevents memory bloat

2. **MongoDB**
   - Indexed on user_id, task_datetime
   - Sharding ready for large user bases

3. **OpenAI API**
   - Per-user API keys
   - Rate limiting handled by user
   - Async calls don't block

4. **Daily Isolation**
   - Prevents context accumulation
   - Automatic cleanup
   - Predictable memory usage
