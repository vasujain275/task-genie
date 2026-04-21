from __future__ import annotations

from app.ai.services.conversation import PocketFlowConversationResponder
from app.application.contracts import (
    ApplicationResult,
    ConversationRequest,
    ConversationResponder,
)
from app.application.context import RequestContext
from app.models.user import User
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ConversationService:
    def __init__(self, responder: ConversationResponder | None = None):
        self._responder = responder or PocketFlowConversationResponder()

    async def handle_message(
        self,
        context: RequestContext,
        text: str | None,
    ) -> ApplicationResult:
        if not text:
            return ApplicationResult(
                kind="rejected",
                message="Please send a text message.",
            )

        user = await User.get_by_telegram_id(int(context.actor_id))
        if not user:
            return ApplicationResult(
                kind="rejected",
                message="User not found. Please use /start to register.",
            )

        if not user.openai_key:
            return ApplicationResult(
                kind="rejected",
                message=(
                    "⚠️ Please configure your OpenAI API key first.\n\n"
                    "Use /settings to configure your API key."
                ),
            )

        logger.info(
            "Processing message for user %s channel=%s session=%s trace=%s",
            user.telegram_id,
            context.channel,
            context.session_id,
            context.trace_id,
        )
        try:
            response = await self._responder.generate(
                ConversationRequest(
                    actor_id=user.telegram_id,
                    user_name=user.name,
                    user_timezone=user.timezone,
                    text=text,
                    openai_key=user.openai_key,
                    channel=context.channel,
                    session_id=context.session_id,
                    trace_id=context.trace_id,
                )
            )
        except Exception as exc:
            from app.ai.services.conversation import APIKeyDecryptionError

            if isinstance(exc, APIKeyDecryptionError):
                return ApplicationResult(
                    kind="rejected",
                    message=(
                        "⚠️ Your saved API key could not be decrypted.\n\n"
                        "Please reconfigure it with /settings."
                    ),
                )
            raise

        if not response.message:
            return ApplicationResult(
                kind=response.kind,
                message="I couldn't process that. Could you try again?",
                interaction=response.interaction,
                data=response.data,
            )

        return ApplicationResult(
            kind=response.kind,
            message=response.message,
            interaction=response.interaction,
            data=response.data,
        )
