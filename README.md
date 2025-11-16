# Task Genie - Quick Reference Guide

## Project Structure

```
task-genie/
├── app/
│   ├── services/              # 🎯 Business Logic Layer
│   │   ├── __init__.py
│   │   ├── nlp_service.py     # AI/NLP processing (Gemini/OpenAI)
│   │   ├── task_service.py    # Task management operations
│   │   └── reminder_service.py # Reminder management operations
│   │
│   ├── bot/
│   │   ├── handlers/          # 🎮 Message Handlers (Thin Layer)
│   │   │   ├── common.py      # Main router - delegates to specific handlers
│   │   │   ├── task.py        # Task creation, confirmation, editing
│   │   │   ├── reminder.py    # Reminder creation, confirmation
│   │   │   ├── settings.py    # Settings configuration handlers
│   │   │   └── start.py       # Start command & onboarding
│   │   │
│   │   ├── keyboards/
│   │   │   └── inline.py      # Inline keyboard definitions
│   │   │
│   │   ├── states.py          # FSM state definitions
│   │   ├── dispatcher.py      # Bot dispatcher setup
│   │   ├── instance.py        # Bot instance
│   │   └── menu.py            # Bot menu commands
│   │
│   ├── models/                # 📊 Database Models
│   │   ├── __init__.py
│   │   ├── user.py            # User model
│   │   ├── task.py            # Task model
│   │   └── reminder.py        # Reminder model
│   │
│   ├── controllers/           # 🌐 API Controllers
│   │   └── settings.py        # Settings API endpoints
│   │
│   ├── utils/                 # 🛠️ Utilities
│   │   ├── logger.py          # Logging setup
│   │   └── security.py        # Security utilities
│   │
│   ├── config.py              # ⚙️ Configuration
│   ├── database.py            # 💾 Database connection
│   ├── main.py                # 🚀 Application entry point
│   └── types.py               # 📝 Type definitions
│
├── logs/                      # 📋 Application logs
├── pyproject.toml             # 📦 Project dependencies
├── ARCHITECTURE.md            # 📚 Architecture documentation
└── README.md                  # Quick reference guide (this file)
```

## Architecture Layers

### 🎯 Services Layer (`app/services/`)
**Purpose:** Contains all business logic, reusable across interfaces

| File | Responsibility |
|------|---------------|
| `nlp_service.py` | AI/NLP processing with Gemini & OpenAI |
| `task_service.py` | Task CRUD operations & management |
| `reminder_service.py` | Reminder CRUD & scheduling |

### 🎮 Handlers Layer (`app/bot/handlers/`)
**Purpose:** Thin routing layer, delegates to services

| File | Handles |
|------|---------|
| `common.py` | Main router - state-based message routing |
| `task.py` | Task creation, confirmation, editing flows |
| `reminder.py` | Reminder creation & confirmation flows |
| `settings.py` | Settings configuration (webapp-based) |
| `start.py` | User onboarding & registration |

### 📊 Models Layer (`app/models/`)
**Purpose:** Database schema definitions

| Model | Purpose |
|-------|---------|
| `User` | User profiles & settings |
| `Task` | Task data & metadata |
| `Reminder` | Reminder scheduling info |

## FSM States

### ConversationMode
- `active` → User can send tasks
- `confirming_task` → Waiting for yes/no
- `editing_task` → Editing task details

### ReminderFlow
- `awaiting_reminder_input` → Waiting for reminder text
- `confirming_reminder` → Confirming reminder
- `selecting_task` → Selecting task for reminder
- `editing_reminder` → Editing reminder time

## Key Design Principles

### ✅ Clean Architecture
- **Separation of Concerns**: Each layer has clear responsibility
- **Dependency Rule**: Handlers → Services → Models
- **Single Responsibility**: One file, one purpose

### ✅ Maintainability
- **Modular**: Easy to add new features
- **Testable**: Services can be tested independently
- **Readable**: Clear naming and documentation

### ✅ Scalability
- **Reusable Services**: Same logic for bot, API, CLI
- **Stateless**: Services don't hold state
- **Async**: Non-blocking operations throughout

## Common Operations

### Adding a New Task Handler
1. Create function in `app/bot/handlers/task.py`
2. Add service call from `app/services/task_service.py`
3. Route in `app/bot/handlers/common.py` based on state
4. Update state in `app/bot/states.py` if needed

### Adding a New Service Method
1. Add method to appropriate service in `app/services/`
2. Add docstring with Args, Returns
3. Add error handling and logging
4. Call from handler when needed

### Adding a New FSM State
1. Define in `app/bot/states.py`
2. Add handler in `app/bot/handlers/common.py`
3. Set state when entering the flow
4. Return to `active` when flow completes

## Development Workflow

### 1. Start Development Server
```bash
python -m app.main
```

### 2. Check Logs
```bash
tail -f logs/bot.log
```

### 3. Run Tests (when implemented)
```bash
pytest tests/
```

## Contributing Guidelines

1. **Follow the layer architecture** - Don't mix concerns
2. **Add docstrings** - Document all functions
3. **Handle errors** - Try-catch in handlers, log in services
4. **Test your code** - Write tests for new features
5. **Keep it clean** - Follow existing code style
6. **Document changes** - Update ARCHITECTURE.md if needed

## Support

For questions or issues:
1. Check `ARCHITECTURE.md` for detailed architecture info
2. Review code comments and docstrings
3. Check logs in `logs/` directory
4. Raise an issue on GitHub

---

**Last Updated:** November 10, 2025
**Version:** 2.0 (Refactored Architecture)
