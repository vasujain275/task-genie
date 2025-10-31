from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.database import init_db
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from aiogram.fsm.storage.redis import RedisStorage
from aiogram import Bot, Dispatcher, Router, types
from app.tg.bot import set_bot_commands_menu

# Router for organizing handlers (aiogram 3.x best practice)
router = Router()

# Import handlers to register them with the router
from app.tg.handlers import messages  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application lifecycle - startup and shutdown"""
    global bot, dp

    client = AsyncIOMotorClient(settings.MONGO_URI)
    await init_db(client)

    storage = RedisStorage.from_url(
        settings.REDIS_URL,
        # state_ttl=3600,  # state expires in 1 hour
        # data_ttl=3600,  # associated data expires in 1 hour
    )

    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    dp.include_router(router=router)

    webhook_url = settings.TELEGRAM_WEBHOOK_URL

    if webhook_url:
        await bot.set_webhook(webhook_url)

    await set_bot_commands_menu(bot)

    print("✅ Bot initialized with Redis FSM storage")

    yield  # Application runs here

    # ========= SHUTDOWN =========
    await bot.delete_webhook()
    await bot.session.close()
    client.close()
    print("🛑 Bot shut down gracefully")


app = FastAPI(title="Task Genie", lifespan=lifespan)

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
    await dp.feed_webhook_update(bot=bot, update=update)
    return {"ok": True}
