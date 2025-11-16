# Pre-Flight Checklist - Before Running the Bot

## ✅ Installation Steps

### 1. Install Dependencies

The following packages were added to `pyproject.toml`:
- `dateparser>=1.2.0` - For natural language date parsing
- `pytz>=2024.1` - For timezone support

**Install all dependencies:**

```bash
# Using uv (recommended)
uv pip install -e .

# OR using pip
pip install -e .
```

### 2. Verify Redis is Running

The bot requires Redis for:
- FSM state storage (aiogram)
- Conversation checkpointing (LangGraph)

**Start Redis:**

```bash
# Start Redis server
redis-server

# Verify it's running
redis-cli ping
# Should return: PONG
```

**Configure Redis URL in `.env`:**

```bash
REDIS_URL=redis://localhost:6379/0
```

### 3. Verify MongoDB is Running

The bot uses MongoDB (via Beanie) for:
- User data
- Tasks
- Reminders

**Start MongoDB:**

```bash
# Start MongoDB service
sudo systemctl start mongodb
# OR
mongod

# Verify it's running
mongo --eval "db.adminCommand('ping')"
```

**Configure MongoDB in `.env`:**

```bash
MONGODB_URL=mongodb://localhost:27017/task_genie
```

### 4. Configure Environment Variables

Create/update `.env` file in project root:

```bash
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token_here

# Database
MONGODB_URL=mongodb://localhost:27017/task_genie

# Redis
REDIS_URL=redis://localhost:6379/0

# Encryption (for storing user API keys)
ENCRYPTION_KEY=your_32_byte_encryption_key_here
```

**Generate encryption key:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 5. User Setup (OpenAI API Key)

Each user needs their own OpenAI API key:

1. User sends `/start` to bot
2. Bot guides through setup:
   - Select timezone
   - Enter OpenAI API key
3. API key is encrypted and stored in MongoDB
4. User can now use natural language task creation

## 🔍 Pre-Run Verification

### Check Python Version

```bash
python --version
# Should be Python 3.11+
```

### Check Installed Packages

```bash
pip list | grep -E "aiogram|beanie|langchain|dateparser|redis"
```

Should show:
- aiogram==3.22.0
- beanie (version)
- langchain-core (version)
- langchain-openai (version)
- langgraph (version)
- dateparser (version)
- redis (version)

### Test Redis Connection

```bash
python -c "
import asyncio
from redis.asyncio import Redis

async def test():
    r = Redis.from_url('redis://localhost:6379/0')
    await r.ping()
    print('✅ Redis connection OK')
    await r.close()

asyncio.run(test())
"
```

### Test MongoDB Connection

```bash
python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    await client.admin.command('ping')
    print('✅ MongoDB connection OK')

asyncio.run(test())
"
```

## 🚀 Running the Bot

### Start the Bot

```bash
python -m app.main
```

**Expected output:**
```
INFO     Starting Task Genie Bot...
INFO     Connecting to MongoDB...
INFO     MongoDB connected successfully
INFO     Initializing Beanie...
INFO     Beanie initialized
INFO     Setting up dispatcher...
INFO     Dispatcher setup complete with all routers registered
INFO     Bot started successfully
```

### Test Basic Flow

1. **Send `/start` to bot:**
   ```
   /start
   ```

2. **Configure timezone:**
   - Click "🌍 Select Timezone"
   - Choose your timezone

3. **Configure OpenAI API key:**
   - Click "🔑 Update OpenAI Key"
   - Send your OpenAI API key
   - Bot will encrypt and save it

4. **Test natural language task creation:**
   ```
   Call mom tomorrow evening
   ```

5. **Expected bot response:**
   ```
   Should I add task **Call Mom** for tomorrow at 6:00 PM?

   🔔 I'll remind you at 5:45 PM.

   Reply **Yes** to confirm or tell me what to change.

   [✅ Yes, create it] [❌ Cancel]
   ```

6. **Click "Yes" or type "yes"**

7. **Expected bot response:**
   ```
   ✅ Task created successfully!

   📋 **Call Mom**
   📅 Due: tomorrow at 6:00 PM

   🔔 Reminder set for tomorrow at 5:45 PM
   ```

## 🐛 Troubleshooting

### Issue: "Import 'dateparser' could not be resolved"

**Solution:**
```bash
pip install dateparser pytz
```

### Issue: "RedisConnectionError"

**Solution:**
- Ensure Redis is running: `redis-cli ping`
- Check REDIS_URL in .env
- Verify firewall isn't blocking port 6379

### Issue: "ServerSelectionTimeoutError" (MongoDB)

**Solution:**
- Ensure MongoDB is running: `sudo systemctl status mongodb`
- Check MONGODB_URL in .env
- Verify firewall isn't blocking port 27017

### Issue: "OpenAI API key not configured"

**Solution:**
- User needs to configure via `/settings`
- Click "🔑 Update OpenAI Key"
- Send valid OpenAI API key starting with "sk-"

### Issue: "Could not understand that task"

**Possible causes:**
- User's OpenAI API key is invalid
- Message was too ambiguous
- OpenAI API is down

**Solution:**
- Verify OpenAI API key is valid
- Ask user to be more specific
- Check OpenAI status: https://status.openai.com/

### Issue: Type errors from Pylance

**Note:** The type errors shown in VSCode are mostly false positives from Pylance's strict type checking. Aiogram guarantees certain fields exist in handler contexts.

**They will not cause runtime errors.**

If you want to suppress them, add to `.vscode/settings.json`:
```json
{
  "python.analysis.typeCheckingMode": "basic"
}
```

## 📊 Monitoring

### Check Redis Keys

```bash
redis-cli
> KEYS checkpoint:*
> GET checkpoint:user_123456_date_2025-11-16
> TTL checkpoint:user_123456_date_2025-11-16
```

### Check MongoDB Collections

```bash
mongo
> use task_genie
> db.users.find().pretty()
> db.tasks.find().pretty()
> db.reminders.find().pretty()
```

### Check Logs

The bot logs to console. For production, configure logging in `app/utils/logger.py`:

```python
# Add file handler
file_handler = logging.FileHandler('logs/task_genie.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
```

## 🎯 Next Steps After Installation

1. ✅ Verify bot responds to `/start`
2. ✅ Test timezone configuration
3. ✅ Test OpenAI API key setup
4. ✅ Test natural language task creation
5. ✅ Verify task saved in MongoDB
6. ✅ Verify reminder saved in MongoDB
7. ✅ Test confirmation flow (Yes/No)
8. ✅ Test cancellation
9. ✅ Test daily conversation isolation
10. ✅ Monitor Redis memory usage

## 📝 Production Considerations

### Before Deploying to Production:

1. **Use environment variables (not .env file):**
   - Set in system/container environment
   - Never commit .env to git

2. **Use managed Redis:**
   - Redis Cloud
   - AWS ElastiCache
   - Azure Cache for Redis

3. **Use managed MongoDB:**
   - MongoDB Atlas
   - AWS DocumentDB
   - Azure Cosmos DB

4. **Enable SSL/TLS:**
   - For Redis connections
   - For MongoDB connections

5. **Set up monitoring:**
   - Application logs
   - Error tracking (Sentry)
   - Performance monitoring

6. **Rate limiting:**
   - Limit OpenAI API calls per user
   - Implement user quotas

7. **Backup strategy:**
   - MongoDB backups
   - Redis persistence configuration

8. **Scale considerations:**
   - Multiple bot instances (webhook mode)
   - Redis cluster for high availability
   - MongoDB sharding for large datasets

## ✨ You're Ready!

Once all checklist items are complete, your bot is ready to parse natural language tasks like:
- "Call mom tomorrow evening"
- "Team meeting next Monday at 10am"
- "Buy groceries by 5pm today"

The bot will intelligently parse, confirm, and create tasks with appropriate reminders! 🎉
