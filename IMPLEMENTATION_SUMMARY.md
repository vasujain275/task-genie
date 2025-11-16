# Task Genie - Natural Language Task Creation Implementation

## 🎉 Implementation Complete!

I've successfully implemented a comprehensive natural language task creation system for your Telegram bot with proper FSM state management, AI-powered parsing, and daily conversation memory.

## 📁 Directory Structure

```
app/
├── ai/                          # NEW: AI processing module
│   ├── __init__.py
│   ├── state.py                 # GraphState and data structures
│   ├── nlp_service.py          # Main NLP service interface
│   ├── checkpointer.py         # Redis-based memory checkpointing
│   ├── README.md               # Comprehensive AI module documentation
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── system.py           # System prompts for AI
│   ├── tools/
│   │   ├── __init__.py
│   │   └── parser.py           # NLP parsing tools
│   └── graph/
│       ├── __init__.py
│       └── task_flow.py        # LangGraph workflow
├── bot/
│   ├── states.py               # UPDATED: Added TaskCreationStates
│   ├── dispatcher.py           # UPDATED: Registered conversation handler
│   ├── handlers/
│   │   ├── conversation.py     # NEW: Natural language message handler
│   │   ├── start.py
│   │   ├── settings.py
│   │   ├── task.py
│   │   └── reminder.py
│   └── keyboards/
│       └── inline.py           # UPDATED: Added task confirmation keyboard
└── models/
    ├── task.py
    ├── reminder.py
    └── user.py
```

## 🚀 Key Features Implemented

### 1. **Natural Language Task Parsing**
- Extracts task title, description, datetime, priority, and tags
- Parses reminder times (explicit or default 15min before task)
- Handles relative dates: "tomorrow", "next Monday", "evening", etc.
- Timezone-aware datetime parsing using `dateparser`

### 2. **Daily Conversation Isolation**
- Each user gets a fresh conversation thread per day
- Conversation ID format: `user_{userId}_date_{YYYY-MM-DD}`
- Prevents context pollution across days
- Automatic cleanup of old conversations (7+ days)

### 3. **Elegant FSM State Management**

```python
class TaskCreationStates(StatesGroup):
    waiting_for_nl_input     # Waiting for natural language input
    confirming_task          # Asking for confirmation
    editing_task_details     # User modifying task
    processing               # Creating task in DB
```

### 4. **Confirmation Flow with Inline Buttons**
- Parses task → generates human-readable confirmation
- User can click "✅ Yes, create it" or "❌ Cancel"
- User can also type "yes" or "no"
- User can modify by typing new input

### 5. **LangGraph Workflow**

```
User: "Call mom tomorrow evening"
        ↓
[parse_input_node] → Extract task/reminder data
        ↓
Check for errors
        ├─ error → Show error message
        └─ success → Generate confirmation
                ↓
Bot: "Should I add task **Call Mom** for tomorrow at 6:00 PM?
      I'll remind you at 5:45 PM."
      [✅ Yes, create it] [❌ Cancel]
        ↓
User clicks "Yes"
        ↓
[create_task_node] → Save to MongoDB
        ↓
Bot: "✅ Task created successfully!
      📋 **Call Mom**
      📅 Due: tomorrow at 6:00 PM
      🔔 Reminder set for 5:45 PM"
```

### 6. **Redis-Based Memory Checkpointing**
- Maintains conversation state across messages
- Uses LangGraph's checkpointing system
- TTL: 24 hours (configurable)
- Thread-safe and scalable

## 📝 Example Usage

### Example 1: Simple Task
```
User: "Call mom tomorrow evening"

Bot: "Should I add task **Call Mom** for tomorrow at 6:00 PM?

🔔 I'll remind you at 5:45 PM.

Reply **Yes** to confirm or tell me what to change."
[✅ Yes, create it] [❌ Cancel]

User: [clicks Yes]

Bot: "✅ Task created successfully!

📋 **Call Mom**
📅 Due: tomorrow at 6:00 PM

🔔 Reminder set for tomorrow at 5:45 PM"
```

### Example 2: Task with Custom Reminder
```
User: "Team meeting next Monday at 10am, remind me 30 minutes before"

Bot: "Should I add task **Team Meeting** for Monday at 10:00 AM?

🔔 I'll remind you at Monday at 9:30 AM.

Reply **Yes** to confirm or tell me what to change."
[✅ Yes, create it] [❌ Cancel]
```

### Example 3: Task with Description
```
User: "Buy groceries by 5pm today - milk, eggs, bread"

Bot: "Should I add task **Buy Groceries** for today at 5:00 PM?

📝 Details: milk, eggs, bread

🔔 I'll remind you at today at 4:45 PM.

Reply **Yes** to confirm or tell me what to change."
[✅ Yes, create it] [❌ Cancel]
```

## 🔧 Configuration

### Dependencies Added to `pyproject.toml`:
```toml
"dateparser>=1.2.0",
"pytz>=2024.1",
```

### Required Environment Variables:
```bash
REDIS_URL=redis://localhost:6379/0
# OpenAI API key is per-user, encrypted in database
```

## 🔄 State Flow

### FSM States (Aiogram):
1. **ConversationMode.active** - Waiting for natural language input
2. **TaskCreationStates.confirming_task** - Asking for confirmation
3. **TaskCreationStates.editing_task_details** - User modifying (future)
4. **TaskCreationStates.processing** - Creating in DB (future)

### Graph Flow (LangGraph):
1. **parse_input** - Parse NL → extract task/reminder
2. **Conditional** - Error or needs confirmation?
3. **create_task** - Save to database
4. **END** - Return response to user

## 🎯 How It Works

### Message Processing Flow:

1. **User sends message** (in `ConversationMode.active` state)
   - Handler: `handle_natural_language_message()`
   - Shows typing indicator
   - Calls `NLPService.process_message()`

2. **NLP Service processes message**
   - Creates/retrieves conversation thread (`user_{id}_date_{YYYY-MM-DD}`)
   - Runs LangGraph workflow with checkpointing
   - Returns parsed task data and confirmation message

3. **Bot asks for confirmation**
   - Changes state to `TaskCreationStates.confirming_task`
   - Shows confirmation message with inline buttons
   - Stores task data in FSM state

4. **User confirms**
   - Handler: `handle_task_confirmation()` or `callback_confirm_task()`
   - Calls `NLPService.confirm_task()`
   - Creates task and reminder in MongoDB
   - Returns to `ConversationMode.active` state

5. **User cancels**
   - Clears pending task
   - Returns to `ConversationMode.active` state

## 🛠️ DateTime Parsing Intelligence

Uses `dateparser` library with custom rules:

- **Relative dates:** "tomorrow", "next week", "next Monday"
- **Time keywords:**
  - "morning" → 9:00 AM
  - "afternoon" → 2:00 PM
  - "evening" → 6:00 PM
  - "tonight" → 8:00 PM
- **Default time:** 9:00 AM if not specified
- **Timezone-aware:** All times converted to user's timezone
- **Future preference:** Defaults to future dates

## 🔒 Security

- OpenAI API keys are encrypted in database using `app.utils.security`
- API keys are decrypted only when needed for LLM calls
- Redis checkpoints use unique thread IDs per user
- TTL on checkpoints prevents indefinite storage

## 📦 Installation & Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # or with uv
   uv pip install -e .
   ```

2. **Ensure Redis is running:**
   ```bash
   redis-server
   ```

3. **Configure OpenAI API key** (per user):
   - User uses `/settings` command
   - Clicks "🔑 Update OpenAI Key"
   - Sends API key (encrypted and stored)

4. **Start the bot:**
   ```bash
   python -m app.main
   ```

## 🧪 Testing

### Manual Testing Flow:

1. Send `/start` to bot
2. Configure timezone and OpenAI API key
3. Send natural language task: `"Call mom tomorrow at 6pm"`
4. Bot should show confirmation with buttons
5. Click "✅ Yes, create it" or type "yes"
6. Bot should create task and show success message
7. Verify task and reminder in database

### Example Test Cases:

```
✅ "Call mom tomorrow evening"
✅ "Team meeting next Monday at 10am"
✅ "Buy groceries by 5pm today - milk, eggs, bread"
✅ "Dentist appointment next week Wednesday at 2pm, remind me 1 hour before"
✅ "Submit report by Friday morning"
✅ "Gym session tonight"
```

## 🚧 Future Enhancements

- [ ] Multi-turn conversations for complex tasks
- [ ] Task editing via conversational updates
- [ ] Support for recurring tasks in NL
- [ ] Voice message transcription
- [ ] Task templates learning from user patterns
- [ ] Batch task creation
- [ ] Smart suggestions based on history

## 📚 Documentation

- **AI Module:** See `app/ai/README.md` for detailed documentation
- **State Management:** See `app/bot/states.py` for FSM states
- **Handlers:** See `app/bot/handlers/conversation.py` for message handling

## 🎊 Summary

Your bot now has:
✅ Natural language task creation with AI parsing
✅ Elegant FSM state management for confirmation flow
✅ Daily conversation isolation (userId + date)
✅ Automatic reminder creation (15min before or custom)
✅ Human-readable confirmations
✅ Inline button support
✅ Timezone-aware datetime parsing
✅ Redis-based memory checkpointing
✅ Error handling and retry logic
✅ Clean, modular architecture

**Ready to parse tasks like:** "Want to call mom tomorrow evening" → Creates task "Call Mom" for tomorrow 6:00 PM with reminder at 5:45 PM! 🎉
