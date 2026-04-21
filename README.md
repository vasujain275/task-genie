# 🧞 Task Genie

Task Genie is a Telegram bot for managing tasks and reminders with natural language.

## Stack

- PocketFlow for orchestration
- LiteLLM for LLM access
- Langfuse tracing via `pocketflow-tracing`
- FastAPI + Aiogram for the app boundary and Telegram adapter
- Beanie + MongoDB for persistence
- short-term conversation history stored in MongoDB

## Architecture

```text
Telegram
  → bot adapter
  → application service boundary
  → PocketFlow conversation engine
  → LiteLLM + task services + history
  → MongoDB / Langfuse
```

### Boundaries

- `app/bot/` maps Telegram updates to request/response objects.
- `app/application/` owns the use-case boundary and result contracts.
- `app/ai/engine/` handles planning, task resolution, execution, tracing, and history.
- `app/models/` contains persistence models.

### Conversation behavior

- supports task creation, editing, deletion, listing, completion, and stats
- keeps short-term conversation history across restarts
- asks for clarification when task references are ambiguous
- uses Langfuse for tracing when enabled

## Setup

### Prerequisites

- Python 3.11+
- MongoDB
- Redis (required for Aiogram FSM / session storage)
- Telegram bot token
- OpenAI-compatible API key through LiteLLM
- A valid Fernet `ENCRYPTION_KEY` (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- Langfuse credentials when tracing is enabled

### Install

```bash
uv sync
cp .env.example .env
```

### Run tests

```bash
uv run pytest -q
```

### Run locally

```bash
uv run uvicorn app.main:app --reload
```

The bot is webhook-only in the current stack: Telegram updates are received at `POST /webhook`, not via long polling.

### Health check

```bash
curl http://localhost:8000/health
```

## Configuration

Copy `.env.example` to `.env` and fill in:

- `MONGO_URI`
- `MONGO_DB_NAME`
- `TELEGRAM_BOT_TOKEN`
- `WEBHOOK_URL`
- `TELEGRAM_WEBHOOK_SECRET_TOKEN`
- `REDIS_URL`
- `ENCRYPTION_KEY`
- `MODEL` or `LITELLM_MODEL`
- `TRACING_ENABLED`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST`
- `LANGFUSE_PROJECT`

## Runtime notes

- `ENCRYPTION_KEY` must be a valid Fernet key, not an arbitrary secret string.
- Tracing only activates when `TRACING_ENABLED=true` **and** the Langfuse credentials/host are set.
- Redis is required for the bot session/FSM layer even if you only run the webhook app.
- Telegram delivery is webhook-based only; configure `WEBHOOK_URL` before expecting inbound updates.
- `GET /health` is available for basic liveness checks.

## Notes

- Telegram is an adapter only; core behavior lives in application services.
- Conversation history is intentionally short-term, not full graph checkpointing.
