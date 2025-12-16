<div align="center">

# 🧞 Task Genie

### AI-Powered Task Management Telegram Bot

*Manage your tasks and reminders using natural language powered by LangGraph AI*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com)
[![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org)

[Features](#-features) • [Architecture](#-architecture) • [Installation](#-installation) • [Usage](#-usage) • [Configuration](#%EF%B8%8F-configuration) • [Development](#-development)

</div>

---

## 📖 Overview

**Task Genie** is an intelligent Telegram bot that helps you manage tasks and reminders through natural conversation. Instead of clicking through menus or using strict commands, just tell the bot what you need to do in plain English!

💬 **Example Conversations:**
- "Remind me to call mom tomorrow at 5pm"
- "I need to submit the report by Friday afternoon"
- "Show me all my pending tasks"
- "Mark the grocery shopping task as done"

The bot uses a **custom LangGraph AI agent** powered by OpenAI to understand your intent, extract task details, and manage your schedule intelligently.

---

## ✨ Features

### 🤖 **Natural Language Processing**
- **Conversational Interface**: Talk to the bot like you would to a human assistant
- **Smart Date Parsing**: Understands relative dates ("tomorrow", "next Monday", "in 3 hours")
- **Timezone Aware**: Automatically handles timezone conversions for accurate scheduling
- **Intent Recognition**: Distinguishes between creating, editing, listing, and deleting tasks

### 📋 **Task Management**
- ✅ Create tasks with titles, descriptions, and due dates
- 🏷️ Organize with tags and categories
- 🎯 Set priority levels (low, medium, high)
- 🔄 Recurring tasks support
- ✏️ Edit existing tasks
- 🗑️ Delete completed or unwanted tasks
- 📊 View task statistics and summaries

### ⏰ **Smart Reminders**
- 🔔 Automatic reminders before task deadlines
- ⏱️ Custom reminder times
- 🌍 Timezone-aware notifications
- 📅 Multiple reminders per task

### 🔐 **Security & Privacy**
- 🔒 Encrypted API key storage (Fernet encryption)
- 👤 Personal workspace for each user
- 🗄️ Secure MongoDB data storage
- 🛡️ No data sharing between users

### 🎨 **User Experience**
- 💬 Interactive Telegram interface with inline keyboards
- 📱 Mobile-friendly design
- ⚙️ Customizable user settings
- 🌐 Timezone configuration
- 📈 Task statistics and insights

---

## 🏗️ Architecture

Task Genie follows a clean, modular architecture built with modern Python tools:

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram User                        │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              Aiogram Bot (Telegram API)                 │
│  • Command Handlers (/start, /settings, /stats)         │
│  • Natural Language Message Handler                     │
│  • FSM State Management (Redis)                         │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph AI Agent                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Custom Graph Workflow:                         │    │
│  │  START → agent → [decide] → tools → agent       │    │
│  │                      ↓                          │    │
│  │                     END                         │    │
│  └─────────────────────────────────────────────────┘    │
│  • Conversation Memory (MongoDB Checkpointing)          │
│  • Message Trimming (last 10 messages)                  │
│  • Daily Thread Reset                                   │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                   LangChain Tools                       │
│  • create_task     • edit_task                          │
│  • list_tasks      • mark_task_done                     │
│  • delete_task     • create_reminder                    │
│  • get_task_stats                                       │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              Beanie ODM Models                          │
│  • User (profiles, settings, encrypted keys)            │
│  • Task (title, datetime, priority, tags)               │
│  • Reminder (remind_at, message)                        │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│                   MongoDB                               │
│  • users                                                │
│  • tasks                                                │
│  • reminders                                            │
└─────────────────────────────────────────────────────────┘
```

### 🧩 **Key Components**

#### **1. Bot Layer** (`app/bot/`)
- **Aiogram Framework**: Handles Telegram API interactions
- **Handlers**: Route commands and messages
  - `start.py`: Welcome flow and user onboarding
  - `conversation.py`: Natural language message processing
  - `settings.py`: User configuration (timezone, API keys)
  - `stats.py`: Task statistics and insights
- **FSM States**: Conversation mode management (Redis-backed)
- **Keyboards**: Inline keyboards for interactive UI

#### **2. AI Layer** (`app/ai/`)
- **Custom LangGraph Agent**: Explicit control over agent behavior
  - ✅ Full transparency and debuggability
  - ✅ Easy to extend with new nodes
  - ✅ Clear flow visualization
  - ✅ No black-box abstractions
- **System Prompts**: Carefully crafted instructions for the LLM
- **LangChain Tools**: Task operations exposed to the agent
- **Memory Management**:
  - MongoDB-based conversation checkpointing
  - Daily thread reset (user_id + date)
  - Last 10 messages retained per thread

#### **3. Models Layer** (`app/models/`)
- **Beanie ODM**: Async MongoDB object-document mapper
- **User Model**: Profiles, settings, encrypted API keys
- **Task Model**: Task data with cascade deletion
- **Reminder Model**: Reminder scheduling information

#### **4. Database Layer**
- **MongoDB**: Primary data store
- **Redis**: FSM state storage for Aiogram
- **Collections**:
  - `users`, `tasks`, `reminders` (app data)
  - `langgraph_checkpoints`, `langgraph_writes` (AI state, 24h TTL)

---

## 🚀 Installation

### **Prerequisites**

- Python 3.11+
- MongoDB (local or cloud)
- Redis (for FSM storage)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key (users provide their own)

### **Local Setup**

1. **Clone the repository**
```bash
git clone https://github.com/vasujain275/task-genie.git
cd task-genie
```

2. **Install dependencies with uv** (recommended)
```bash
# Install uv if you haven't already
pip install uv

# Install dependencies
uv sync
```

Or with pip:
```bash
pip install -e .
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run MongoDB and Redis**
```bash
# MongoDB (local)
mongod

# Redis (local)
redis-server
```

5. **Start the bot**
```bash
# Development mode
uv run uvicorn app.main:app --reload

# Or with polling (no webhook)
uv run python -m app.main
```

### **Docker Setup**

#### **Quick Start (All-in-One)**
Uses prebuilt Docker Hub image with MongoDB and Redis:
```bash
# Create .env file from example
cp .env.example .env
# Edit .env with your configuration (TELEGRAM_BOT_TOKEN, ENCRYPTION_KEY, etc.)

# Start all services (MongoDB, Redis, App)
docker compose up -d

# View logs
docker compose logs -f app

# Stop all services
docker compose down
```

#### **Development Setup**
Builds app from local source instead of Docker Hub:
```bash
# Start development environment
docker compose -f docker-compose.dev.yaml up -d

# Rebuild after code changes
docker compose -f docker-compose.dev.yaml up -d --build

# Stop development environment
docker compose -f docker-compose.dev.yaml down
```

#### **Production Deployment**
App-only setup (requires external MongoDB and Redis):
```bash
# Ensure .env has external MONGO_URI and REDIS_URL
# Example: MONGO_URI=mongodb://user:pass@host:port
#          REDIS_URL=redis://host:port

# Start production app
docker compose -f docker-compose.prod.yaml up -d

# Scale with multiple instances
docker compose -f docker-compose.prod.yaml up -d --scale app=3
```

#### **Docker Environment Variables**

For docker-compose.yaml and docker-compose.dev.yaml, add to your `.env`:
```env
# MongoDB credentials (for Docker services)
MONGO_USERNAME=admin
MONGO_PASSWORD=your_secure_password

# Optional: Custom Docker image
DOCKER_IMAGE=vasujain275/task-genie:latest
```

> **Note**: MongoDB and Redis URLs are automatically configured in Docker Compose to use service names (`mongodb:27017`, `redis:6379`)

---

## 📱 Usage

### **First Time Setup**

1. **Start a chat with your bot** on Telegram
2. Send `/start` command
3. **Configure your settings**:
   - Set your timezone (e.g., "America/New_York", "Asia/Kolkata")
   - Provide your OpenAI API key (securely encrypted)
4. Start chatting!

### **Creating Tasks**

Just tell the bot what you need to do:

```
You: Remind me to buy groceries tomorrow at 5pm

Bot: ✅ I've created a reminder: "Buy groceries"
     Due: Tomorrow at 5:00 PM
     I'll remind you 15 minutes before!
```

```
You: Team meeting next Monday at 10am with high priority

Bot: ✅ Created high priority task: "Team meeting"
     Scheduled: Monday, Nov 18 at 10:00 AM
```

### **Managing Tasks**

```
You: Show me all my pending tasks

Bot: 📋 You have 3 pending tasks:
     1. 🔴 Team meeting - Mon, Nov 18, 10:00 AM
     2. 🟡 Buy groceries - Tue, Nov 19, 5:00 PM
     3. 🟢 Call mom - Wed, Nov 20, 6:00 PM
```

```
You: Mark the grocery task as done

Bot: ✅ Marked "Buy groceries" as complete!
```

### **Available Commands**

- `/start` - Start the bot and configure settings
- `/settings` - Update timezone or API key
- `/stats` - View task statistics
- `/help` - Get help and usage examples

---

## ⚙️ Configuration

### **Environment Variables**

Create a `.env` file in the root directory:

```env
# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=task_genie

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# Webhook (optional - for production)
WEBHOOK_URL=https://yourdomain.com/webhook

# Redis (for FSM storage)
REDIS_URL=redis://localhost:6379/0

# Security
ENCRYPTION_KEY=your_fernet_encryption_key

# Logging
LOG_LEVEL=INFO

# LLM Configuration
LLM=gpt-5-nano

# LangSmith (optional - for debugging)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=task-genie
```

### **Generating Encryption Key**

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### **User Settings**

Each user can configure:
- **Timezone**: For accurate task scheduling
- **OpenAI API Key**: Personal API key (encrypted at rest)

---

## 🛠️ Development

### **Project Structure**

```
task-genie/
├── app/
│   ├── ai/                      # AI/LLM components
│   │   ├── graph/
│   │   │   └── agent.py        # Custom LangGraph workflow
│   │   ├── prompts/
│   │   │   └── system.py       # System prompts
│   │   └── tools/
│   │       └── task_tools.py   # LangChain tools
│   ├── bot/                     # Telegram bot components
│   │   ├── handlers/           # Message/command handlers
│   │   ├── keyboards/          # Inline keyboards
│   │   ├── dispatcher.py       # Router setup
│   │   ├── instance.py         # Bot instance
│   │   ├── menu.py             # Bot commands menu
│   │   └── states.py           # FSM states
│   ├── models/                  # Database models
│   │   ├── user.py
│   │   ├── task.py
│   │   └── reminder.py
│   ├── utils/                   # Utilities
│   │   ├── logger.py
│   │   └── security.py
│   ├── config.py               # Configuration
│   ├── database.py             # DB initialization
│   └── main.py                 # FastAPI entry point
├── logs/                        # Application logs
├── .env                         # Environment variables
├── Dockerfile                   # Docker configuration
├── docker-compose.yml           # Docker Compose setup
├── pyproject.toml              # Project dependencies
└── README.md                    # This file
```

### **Adding New Features**

#### **Add a New Tool for the Agent**

1. Define the tool in `app/ai/tools/task_tools.py`:
```python
@tool
async def my_new_tool(user_id: int, param: str) -> str:
    """Description for the LLM"""
    # Implementation
    return "Result"
```

2. Add to `TASK_TOOLS` list:
```python
TASK_TOOLS = [
    create_task,
    list_tasks,
    my_new_tool,  # Your new tool
]
```

The agent will automatically have access to it!

#### **Add a New Node to the Graph**

In `app/ai/graph/agent.py`:

```python
def my_custom_node(state: AgentState) -> dict:
    """Custom node logic"""
    # Process state
    return {"messages": [...]}

# Add to workflow
workflow.add_node("my_node", my_custom_node)
workflow.add_edge("agent", "my_node")
```

### **Code Quality**

```bash
# Format code with black
uv run black app/

# Lint with ruff
uv run ruff check app/

# Run pre-commit hooks
pre-commit run --all-files
```

### **Logging**

Logs are written to `logs/` directory with rotation:
- `app.log` - Application logs
- `errors.log` - Error logs only

Configure log level in `.env`:
```env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## 🔧 Deployment

### **Production Deployment Options**

#### **Option 1: All-in-One Docker (Development/Testing)**
Includes MongoDB and Redis in the same compose stack:
```bash
# Clone the repository
git clone https://github.com/vasujain275/task-genie.git
cd task-genie

# Set up environment
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN, ENCRYPTION_KEY, etc.

# Add MongoDB credentials to .env
echo "MONGO_USERNAME=admin" >> .env
echo "MONGO_PASSWORD=your_secure_password" >> .env

# Start all services
docker compose up -d

# Check logs
docker compose logs -f app
```

#### **Option 2: Production Deployment (External Services)**
App-only deployment with cloud MongoDB and Redis:
```bash
# Set up .env with external services
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/task_genie
REDIS_URL=redis://your-redis-host:6379
TELEGRAM_BOT_TOKEN=your_bot_token
WEBHOOK_URL=https://yourdomain.com/webhook
ENCRYPTION_KEY=your_encryption_key

# Deploy app only
docker compose -f docker-compose.prod.yaml up -d
```

#### **Option 3: Development with Local Build**
Build and run from source code:
```bash
# Start development stack
docker compose -f docker-compose.dev.yaml up -d

# Rebuild after changes
docker compose -f docker-compose.dev.yaml up -d --build
```

### **Webhook Setup (Production)**

1. **Set up webhook** in your `.env`:
```env
WEBHOOK_URL=https://yourdomain.com/webhook
```

2. **Configure reverse proxy** (Nginx example):
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /webhook {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. **Restart the app** to register webhook with Telegram

### **Docker Image Tags**

Available on Docker Hub: `vasujain275/task-genie`
- `latest` - Latest stable release
- `v1.0.0` - Specific version tags
- `dev` - Development builds

### **Health Checks**

All Docker Compose files include health checks:
- MongoDB: Database ping
- Redis: Redis CLI ping
- App: HTTP health endpoint at `/health`

Monitor with:
```bash
docker compose ps
```

### **Scaling Considerations**

- **MongoDB**: Use MongoDB Atlas for managed cloud database
- **Redis**: Use Redis Cloud or AWS ElastiCache
- **Workers**: Scale uvicorn workers based on CPU cores
- **Caching**: Implement user data caching for frequent queries

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### **Code Style**

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for functions and classes
- Add comments for complex logic

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **[LangChain](https://langchain.com)** & **[LangGraph](https://langchain.com/langgraph)** - AI agent framework
- **[Aiogram](https://aiogram.dev)** - Elegant Telegram Bot framework
- **[FastAPI](https://fastapi.tiangolo.com)** - Modern web framework
- **[Beanie](https://beanie-odm.dev)** - Async MongoDB ODM
- **[OpenAI](https://openai.com)** - Language model provider

---

## 📞 Support

For questions, issues, or feature requests:

1. 📖 Check the documentation in this README
2. 🐛 [Open an issue](https://github.com/vasujain275/task-genie/issues) on GitHub
3. 💬 Review code comments and docstrings
4. 📊 Check logs in `logs/` directory

---

<div align="center">

**Made with ❤️ by [Vasu Jain](https://github.com/vasujain275)**

⭐ Star this repo if you find it helpful!

</div>
