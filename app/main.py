from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient

from aiogram import types

from app.config import settings
from app.database import init_db
from app.bot.menu import set_bot_commands_menu
from app.bot.instance import bot
from app.bot.dispatcher import setup_dispatcher
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application lifecycle - startup and shutdown"""
    logger.info("Starting application initialization...")

    try:
        client = AsyncIOMotorClient(settings.MONGO_URI)
        logger.info("MongoDB client created")

        await init_db(client)
        logger.info("Database initialized")

        # Setup dispatcher with all handlers
        dp = setup_dispatcher()
        logger.info("Dispatcher configured with handlers")

        if settings.WEBHOOK_URL:
            await bot.set_webhook(settings.WEBHOOK_URL)
            logger.info(f"Webhook set to: {settings.WEBHOOK_URL}")
        else:
            logger.warning("No webhook URL configured - bot will not receive updates")

        await set_bot_commands_menu(bot)
        logger.info("Bot commands menu configured")

        logger.info("✅ Bot initialized successfully with Redis FSM storage")

        # Store dp in app state for access in webhook handler
        app.state.dp = dp

        yield  # Application runs here

        # ========= SHUTDOWN =========
        logger.info("Shutting down application...")
        await bot.delete_webhook()
        await bot.session.close()
        client.close()
        logger.info("🛑 Bot shut down gracefully")

    except Exception as e:
        logger.error(f"Error during application lifecycle: {e}", exc_info=True)
        raise


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
    logger.debug("Health check requested")
    return {"status": "ok"}


async def process_update(update: types.Update, dp):
    """Process update in background without blocking webhook response"""
    try:
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        logger.error(f"Error processing update in background: {e}", exc_info=True)


@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive updates from Telegram and process them asynchronously"""
    try:
        update_data = await request.json()
        logger.info("=== Webhook update received ===")
        logger.info(f"Update keys: {update_data.keys()}")

        # Log message details if present
        if "message" in update_data:
            msg = update_data["message"]
            logger.info(f"Message content_type: {msg.get('content_type', 'N/A')}")
            logger.info(f"Message keys: {msg.keys()}")
            if "web_app_data" in msg:
                logger.info(f"WEB APP DATA FOUND: {msg['web_app_data']}")

        update = types.Update(**update_data)

        # Process update in background - IMMEDIATELY return to Telegram
        background_tasks.add_task(process_update, update, request.app.state.dp)

        # Return immediately - don't wait for processing to complete
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {"ok": False}
        return {"ok": False}
