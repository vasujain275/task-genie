from __future__ import annotations

from app.ai.engine.tracing import normalize_session_id
from app.application.contracts import ConversationRequest, ConversationResponse
from app.utils.security import decrypt_api_key


class APIKeyDecryptionError(ValueError):
    pass


class PocketFlowConversationResponder:
    async def generate(self, request: ConversationRequest) -> ConversationResponse:
        from app.ai.engine.flow import build_conversation_flow

        flow = build_conversation_flow()
        channel = getattr(request, "channel", "telegram")
        session_id = normalize_session_id(
            channel, getattr(request, "session_id", ""), request.actor_id
        )
        try:
            decrypted_key = decrypt_api_key(request.openai_key)
        except ValueError as exc:
            raise APIKeyDecryptionError(
                "Your saved API key could not be decrypted. Please reconfigure it with /settings."
            ) from exc

        request = ConversationRequest(
            actor_id=request.actor_id,
            user_name=request.user_name,
            user_timezone=request.user_timezone,
            text=request.text,
            openai_key=decrypted_key,
            channel=channel,
            session_id=session_id,
            trace_id=getattr(request, "trace_id", ""),
        )
        return await flow.generate(request)
