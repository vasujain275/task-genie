from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient

from aiogram import types

from app.config import settings
from app.database import init_db
from app.bot.menu import set_bot_commands_menu
from app.bot.instance import bot
from app.bot.dispatcher import setup_dispatcher
from app.services.reminder_scheduler import (
    start_reminder_scheduler,
    stop_reminder_scheduler,
)
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
            webhook_kwargs = {}
            if settings.TELEGRAM_WEBHOOK_SECRET_TOKEN:
                webhook_kwargs["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET_TOKEN

            await bot.set_webhook(settings.WEBHOOK_URL, **webhook_kwargs)
            logger.info(f"Webhook set to: {settings.WEBHOOK_URL}")
        else:
            logger.warning("No webhook URL configured - bot will not receive updates")

        await set_bot_commands_menu(bot)
        logger.info("Bot commands menu configured")

        # Start reminder scheduler
        start_reminder_scheduler()
        logger.info("Reminder scheduler started")

        logger.info("✅ Bot initialized successfully with Redis FSM storage")

        # Store dp in app state for access in webhook handler
        app.state.dp = dp

        yield  # Application runs here

        # ========= SHUTDOWN =========
        logger.info("Shutting down application...")

        # Stop reminder scheduler
        stop_reminder_scheduler()

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
        if settings.TELEGRAM_WEBHOOK_SECRET_TOKEN:
            token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if token != settings.TELEGRAM_WEBHOOK_SECRET_TOKEN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid webhook secret token",
                )

        try:
            update_data = await request.json()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Telegram update payload",
            ) from exc
        logger.info("Webhook update received keys=%s", sorted(update_data.keys()))

        if "message" in update_data:
            msg = update_data["message"]
            logger.info(
                "Webhook message metadata chat_id=%s message_id=%s has_web_app_data=%s",
                msg.get("chat", {}).get("id"),
                msg.get("message_id"),
                "web_app_data" in msg,
            )

        try:
            update = types.Update(**update_data)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Telegram update payload",
            ) from exc

        dp = getattr(request.app.state, "dp", None)
        if dp is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Dispatcher is not configured",
            )

        # Process update in background - IMMEDIATELY return to Telegram
        background_tasks.add_task(process_update, update, dp)

        # Return immediately - don't wait for processing to complete
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        ) from e
