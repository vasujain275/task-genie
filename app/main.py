from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient

from aiogram import types

from app.config import settings
from app.database import init_db
from app.bot.menu import set_bot_commands_menu
from app.bot.instance import bot
from app.bot.dispatcher import setup_dispatcher
from app.controllers.settings import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application lifecycle - startup and shutdown"""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    await init_db(client)

    webhook_url = f"{settings.TELEGRAM_WEBAPP_URL}/webhook"

    # Setup dispatcher with all handlers
    dp = setup_dispatcher()

    if webhook_url:
        await bot.set_webhook(webhook_url)

    await set_bot_commands_menu(bot)

    print("✅ Bot initialized with Redis FSM storage")

    # Store dp in app state for access in webhook handler
    app.state.dp = dp

    yield  # Application runs here

    # ========= SHUTDOWN =========
    await bot.delete_webhook()
    await bot.session.close()
    client.close()
    print("🛑 Bot shut down gracefully")


app = FastAPI(title="Task Genie", lifespan=lifespan)

# Include routers
app.include_router(settings_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    """Receive updates from Telegram"""
    update = types.Update(**await request.json())
    await request.app.state.dp.feed_webhook_update(bot=bot, update=update)
    return {"ok": True}
