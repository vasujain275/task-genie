# MongoDB Checkpointing Migration

## Summary

Migrated LangGraph checkpointing from **Redis** to **MongoDB** using `AsyncMongoDBSaver` for a cleaner, simpler architecture.

## What Changed

### 1. Checkpointer Implementation (`app/ai/checkpointer.py`)

**Before (Redis):**
- Custom `RedisCheckpointer` class extending `BaseCheckpointSaver`
- Manual implementation of `get()`, `put()`, `list()` methods
- Pickle serialization
- Manual connection management
- Custom cleanup function

**After (MongoDB):**
- Uses built-in `AsyncMongoDBSaver` from `langgraph-checkpoint-mongodb`
- No custom class needed
- Automatic serialization
- Connection managed by Motor client
- Automatic TTL-based cleanup

### 2. Code Simplification

**Old Implementation: ~200 lines**
```python
class RedisCheckpointer(BaseCheckpointSaver):
    def __init__(self, redis_url, ttl):
        # Custom initialization

    async def get(self, config):
        # Custom Redis get logic with pickle

    async def put(self, config, checkpoint):
        # Custom Redis put logic with pickle

    async def list(self, config):
        # Custom list logic
```

**New Implementation: ~75 lines**
```python
async def get_checkpointer() -> AsyncMongoDBSaver:
    global _checkpointer
    if _checkpointer is None:
        client = AsyncIOMotorClient(settings.MONGO_URI)
        _checkpointer = AsyncMongoDBSaver(
            client=client,
            db_name=settings.MONGO_DB_NAME,
            checkpoint_collection_name="langgraph_checkpoints",
            writes_collection_name="langgraph_writes",
            ttl=86400  # 24 hours
        )
    return _checkpointer
```

### 3. MongoDB Collections

Two collections auto-created with TTL indexes:

1. **`langgraph_checkpoints`** - Stores conversation state
2. **`langgraph_writes`** - Stores intermediate writes

Both have 24-hour TTL for automatic cleanup.

### 4. Configuration

**Removed:**
- Complex manual cleanup logic
- Custom pickle serialization
- Redis-specific error handling

**Kept:**
- Daily conversation isolation pattern
- Thread ID format: `user_{user_id}_date_{YYYY-MM-DD}`
- Same `get_conversation_id()` function

## Benefits

### 1. **Simpler Code**
- 60% reduction in code (200 → 75 lines)
- No custom serialization logic
- No manual cleanup needed

### 2. **Better Integration**
- Official LangGraph MongoDB checkpointer
- Consistent with LangGraph best practices
- Well-tested and maintained

### 3. **Unified Data Store**
- MongoDB for both:
  - Application data (tasks, users, reminders)
  - Conversation checkpoints
- One connection string to manage
- Easier backup/restore

### 4. **Automatic Cleanup**
- MongoDB TTL indexes handle expiration
- No background tasks needed
- More reliable than manual cleanup

### 5. **Type Safety**
- No more `# type: ignore[override]` comments
- Uses proper LangGraph interfaces
- Better IDE support

## Storage Architecture

### Before
```
Redis (REDIS_URL)
├── FSM States (aiogram)
│   └── user:{user_id}:state
└── Checkpoints (LangGraph)
    └── checkpoint:{thread_id}

MongoDB (MONGO_URI)
└── Application Data
    ├── users
    ├── tasks
    └── reminders
```

### After
```
Redis (REDIS_URL)
└── FSM States (aiogram only)
    └── user:{user_id}:state

MongoDB (MONGO_URI)
├── Application Data
│   ├── users
│   ├── tasks
│   └── reminders
└── LangGraph Checkpoints
    ├── langgraph_checkpoints
    └── langgraph_writes
```

## Migration Steps

### 1. Update Dependencies

**pyproject.toml:**
```diff
dependencies = [
    ...
    "redis>=7.0.1",  # Still needed for aiogram FSM
+   "langgraph-checkpoint-mongodb>=2.0.8",
    "langgraph>=1.0.0",
    ...
]
```

### 2. Install New Package

```bash
uv pip install -e .
```

### 3. Update Configuration

**config.py:**
```python
# Redis still needed for aiogram FSM storage
REDIS_URL: str = ""  # For aiogram FSM storage

# MongoDB now handles both app data and checkpointing
MONGO_URI: str = ""
MONGO_DB_NAME: str = ""
```

### 4. No Code Changes Needed

The `NLPService` uses the checkpointer interface, so no changes needed:

```python
# This still works exactly the same
self.checkpointer = await get_checkpointer()
self.graph = workflow.compile(checkpointer=self.checkpointer)
```

## Usage

### Daily Isolation (Unchanged)

```python
from app.ai import get_conversation_id

# Each day = new thread
thread_id = get_conversation_id(user_id=12345)
# "user_12345_date_2025-11-16"
```

### Process Message (Unchanged)

```python
from app.ai import get_nlp_service

nlp_service = await get_nlp_service()
result = await nlp_service.process_message(
    user_id=12345,
    user_message="Call mom tomorrow",
    user_name="John",
    user_timezone="UTC"
)
```

## Environment Variables

```env
# MongoDB (for app data + checkpointing)
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=task_genie

# Redis (for aiogram FSM only)
REDIS_URL=redis://localhost:6379/0

# OpenAI (for NLP)
OPENAI_API_KEY=sk-...

# Bot
TELEGRAM_BOT_TOKEN=...
```

## Testing

### Verify MongoDB Connection

```bash
# Connect to MongoDB
mongosh mongodb://localhost:27017/task_genie

# Check collections
show collections
# Should see: langgraph_checkpoints, langgraph_writes

# Check TTL indexes
db.langgraph_checkpoints.getIndexes()
# Should have TTL index on expireAt field
```

### Verify Checkpointing Works

1. Start bot and send a message
2. Check MongoDB:
```javascript
db.langgraph_checkpoints.find().pretty()
```
3. Should see checkpoint with thread_id like `user_12345_date_2025-11-16`

## Cleanup

Checkpoints automatically expire after 24 hours via MongoDB TTL indexes. No manual cleanup needed!

### Old Cleanup (Removed)
```python
# No longer needed!
await cleanup_old_checkpoints(days_to_keep=7)
```

### New Cleanup (Automatic)
MongoDB TTL monitor runs every 60 seconds and removes expired documents automatically.

## Rollback Plan

If needed, revert by:

1. Restore `app/ai/checkpointer.py` from git history
2. Remove `langgraph-checkpoint-mongodb` from `pyproject.toml`
3. Run `uv pip install -e .`

## Performance

### Storage
- **Before**: Pickled Python objects in Redis
- **After**: BSON documents in MongoDB
- **Size**: Similar (both compress well)

### Speed
- **Before**: In-memory Redis (very fast)
- **After**: MongoDB with indexes (fast enough)
- **Impact**: Negligible for conversation checkpointing

### Scalability
- MongoDB replication for HA
- Sharding for large datasets
- Better for long-term persistence

## Conclusion

✅ **Simpler** - 60% less code
✅ **Cleaner** - Official LangGraph integration
✅ **Unified** - One database for everything
✅ **Automatic** - TTL-based cleanup
✅ **Better** - Proper type safety

Migration complete with zero breaking changes to the API!
