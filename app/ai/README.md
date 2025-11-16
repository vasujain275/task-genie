# AI Module - Natural Language Processing

This module handles natural language processing for task management using a **custom LangGraph agent**.

## Architecture

```
app/ai/
├── graph/
│   └── agent.py         # Custom LangGraph workflow (nodes, edges, state)
├── prompts/
│   └── system.py        # System prompts for the agent
└── tools/
    └── task_tools.py    # LangChain tools for task operations
```

## Custom LangGraph Agent

We use a **custom graph implementation** instead of prebuilt agents for:
- ✅ Full control over agent behavior
- ✅ Easy to understand and debug
- ✅ Simple to extend with new nodes
- ✅ Clear flow visualization
- ✅ Maintainable codebase

### Graph Structure

```
START
  ↓
[agent] ←─────┐
  ↓           │
[should_continue?]
  ├─→ tools ──┘
  └─→ END
```

### Node Details

1. **`agent` node**:
   - Calls LLM with tools bound
   - LLM decides whether to respond directly or call tools
   - Returns AIMessage (with or without tool calls)

2. **`should_continue` function**:
   - Routes based on last message
   - If tool calls present → route to `tools` node
   - If no tool calls → route to `END`

3. **`tools` node**:
   - Executes tool calls in parallel
   - Returns ToolMessage results
   - Loops back to `agent` node

### State Definition

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add]  # Append-only
    user_id: int
    user_name: str
    user_timezone: str
```

## How It Works

### 1. User sends message

```python
agent = create_task_agent(
    openai_key="sk-...",
    user_id=123,
    user_name="John",
    user_timezone="America/New_York"
)

response = await agent.ainvoke({
    "messages": [HumanMessage(content="Remind me to call mom tomorrow at 5pm")]
})
```

### 2. Agent flow

1. System message is prepended (with current time, user info)
2. Graph starts at `agent` node
3. LLM sees the tools available and user message
4. LLM decides to call `create_task` tool
5. Router sends to `tools` node
6. Tool executes (creates task in DB)
7. Returns to `agent` node with tool result
8. LLM generates friendly confirmation message
9. No more tool calls → ends

### 3. Response

```python
"✅ I've set a reminder to call mom tomorrow at 5:00 PM!
I'll remind you 15 minutes before."
```
1. **parse_input_node**: Extracts task/reminder data from natural language
2. **create_task_node**: Saves to database after user confirmation

### 4. Natural Language Parsing

Uses OpenAI GPT-4o-mini to extract:
- Task title and description
- Due dates (relative or absolute)
- Reminder times
- Timezone-aware datetime parsing

## Usage

### Initialize NLP Service

```python
from app.ai import get_nlp_service

nlp_service = await get_nlp_service()
```

### Process Natural Language Message

```python
result = await nlp_service.process_message(
    user_id=12345,
    user_message="Call mom tomorrow at 6pm",
    user_name="John",
    user_timezone="America/New_York"
)

if result["needs_confirmation"]:
    # Show confirmation message to user
    print(result["confirmation_message"])
```

### Confirm Task Creation

```python
result = await nlp_service.confirm_task(
    user_id=12345,
    user_name="John"
)

if result["task_created"]:
    print("Task created successfully!")
```

## Configuration

Required environment variables:

```env
# MongoDB (used for both data and checkpointing)
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=task_genie

# OpenAI API (for NLP parsing)
OPENAI_API_KEY=sk-...

# Redis (for aiogram FSM storage only)
REDIS_URL=redis://localhost:6379/0
```

## MongoDB Collections

### LangGraph Collections (auto-created)
- `langgraph_checkpoints` - Conversation state with 24h TTL
- `langgraph_writes` - Intermediate writes with 24h TTL

### Application Collections (Beanie models)
- `users` - User settings and preferences
- `tasks` - Task documents
- `reminders` - Reminder documents

## State Management

### FSM States (aiogram - stored in Redis)
- `waiting_for_nl_input` - Waiting for natural language message
- `confirming_task` - Waiting for user confirmation
- `editing_task_details` - User editing task details
- `processing` - Creating task in database

### Graph State (LangGraph - stored in MongoDB)
```python
GraphState = TypedDict("GraphState", {
    "user_message": str,
    "user_id": int,
    "task_data": Optional[TaskData],
    "reminder_data": Optional[ReminderData],
    "needs_confirmation": bool,
    "user_confirmed": Optional[bool],
    # ... more fields
})
```

## Dependencies

```toml
langgraph>=1.0.0                      # Graph workflow
langgraph-checkpoint-mongodb>=2.0.8   # MongoDB checkpointing
langchain-openai>=1.0.0               # OpenAI integration
dateparser>=1.2.0                     # Datetime parsing
pytz>=2024.1                          # Timezone support
motor>=3.7.1                          # MongoDB async driver
redis>=7.0.1                          # aiogram FSM storage
```

## Examples

### Example 1: Simple Task

```
User: "Buy groceries tomorrow"
```

Parsed:
- Title: "Buy groceries"
- Due: Tomorrow, end of day
- Reminder: None

### Example 2: Task with Reminder

```
User: "Call mom tomorrow evening and remind me 1 hour before"
```

Parsed:
- Title: "Call mom"
- Due: Tomorrow, 6:00 PM (evening)
- Reminder: 1 hour before (5:00 PM)

### Example 3: Specific DateTime

```
User: "Team meeting on December 15th at 2:30 PM"
```

Parsed:
- Title: "Team meeting"
- Due: 2025-12-15 14:30:00
- Reminder: None

## Cleanup

Checkpoints automatically expire after 24 hours via MongoDB TTL indexes. No manual cleanup needed!
