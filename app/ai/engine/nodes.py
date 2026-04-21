from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pocketflow import AsyncNode

from app.ai.engine.history import ConversationHistoryService, build_clarification_hint
from app.ai.engine.tracing import get_active_trace_context, sanitize_request_message
from app.ai.engine.schemas import PlannerPlan
from app.ai.prompts.system import PLANNER_SYSTEM_PROMPT
from app.utils.logger import setup_logger
from app.application.contracts import (
    ApplicationInteraction,
    ApplicationResult,
    ConversationRequest,
    ConversationResponse,
)


logger = setup_logger(__name__)


def _request_from_shared(shared: dict) -> ConversationRequest:
    llm = shared.get("llm")
    request = shared.get("request")
    if isinstance(request, ConversationRequest):
        return request
    return ConversationRequest(
        actor_id=shared.get("actor_id", 0),
        user_name=shared.get("user_name", ""),
        user_timezone=shared.get("user_timezone", "UTC"),
        text=shared.get("text", ""),
        openai_key=getattr(llm, "_api_key", "") or shared.get("openai_key", ""),
        channel=shared.get("channel", "telegram"),
        session_id=shared.get("session_id", ""),
        trace_id=shared.get("trace_id", ""),
    )


class LoadRequestNode(AsyncNode):
    def __init__(self, history: ConversationHistoryService | None = None):
        super().__init__()
        self._history = history or ConversationHistoryService()

    async def prep_async(self, shared: dict):
        return {
            "actor_id": shared["actor_id"],
            "user_name": shared["user_name"],
            "user_timezone": shared["user_timezone"],
            "text": shared["text"],
            "channel": shared["channel"],
            "session_id": shared["session_id"],
            "trace_id": shared.get("trace_id", ""),
            "llm": shared["llm"],
        }

    async def exec_async(self, payload: dict):
        request = _request_from_shared(payload)
        try:
            current_datetime = datetime.now(ZoneInfo(request.user_timezone))
        except (ZoneInfoNotFoundError, ValueError, Exception):
            logger.warning(
                "Invalid timezone '%s'; falling back to UTC", request.user_timezone
            )
            current_datetime = datetime.now(ZoneInfo("UTC"))
            timezone_warning = request.user_timezone
        else:
            timezone_warning = None

        recent_turns = await self._history.load_recent_turns(
            actor_id=request.actor_id,
            channel=request.channel,
            session_id=request.session_id,
        )
        recent_clarification_context = self._history.recent_clarification_context(
            recent_turns
        )
        trace_context = get_active_trace_context()
        return {
            "channel": request.channel,
            "actor_id": request.actor_id,
            "session_id": request.session_id,
            "recent_turns": recent_turns,
            "history_summary": self._history.render_turns(recent_turns),
            "recent_clarification_context": recent_clarification_context,
            "clarification_hint": build_clarification_hint(
                recent_clarification_context
            ),
            "current_datetime": current_datetime.isoformat(),
            "timezone_warning": timezone_warning,
            "trace_context": trace_context,
        }

    async def post_async(self, shared: dict, _prep_res, exec_res):
        shared.update(exec_res)
        return "default"


class PlanIntentNode(AsyncNode):
    def __init__(self, llm):
        super().__init__()
        self._llm = llm

    async def prep_async(self, shared: dict):
        return {
            "actor_id": shared["actor_id"],
            "user_name": shared["user_name"],
            "user_timezone": shared["user_timezone"],
            "text": shared["text"],
            "channel": shared["channel"],
            "session_id": shared["session_id"],
            "trace_id": shared.get("trace_id", ""),
            "history_summary": shared.get("history_summary"),
            "clarification_hint": shared.get("clarification_hint"),
            "current_datetime": shared.get("current_datetime"),
            "trace_context": shared.get("trace_context"),
            "llm": shared["llm"],
        }

    async def exec_async(self, payload: dict):
        request = _request_from_shared(payload)
        history_summary = payload.get("history_summary")
        clarification_hint = payload.get("clarification_hint")
        history_block = f"History:\n{history_summary}\n" if history_summary else ""
        clarification_block = (
            f"Clarification Context:\n{clarification_hint}\n"
            if clarification_hint
            else ""
        )
        schema = PlannerPlan.model_json_schema()
        try:
            trace_context = get_active_trace_context()
            raw = await self._llm.complete_json(
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"User: {request.user_name}\n"
                            f"Timezone: {request.user_timezone}\n"
                            f"Now: {payload.get('current_datetime')}\n"
                            f"{history_block}"
                            f"{clarification_block}"
                            f"Message: {request.text}"
                        ),
                    },
                ],
                api_key=request.openai_key,
                schema=schema,
                request_message=sanitize_request_message(
                    request_text=request.text,
                    history_summary=history_summary,
                    clarification_hint=clarification_hint,
                ),
                trace_context=trace_context,
            )
            return PlannerPlan.model_validate(raw)
        except ValueError as exc:
            if "task_datetime is required for create_task" in str(exc):
                return ApplicationResult(
                    kind="rejected",
                    message="Please include a date and time for the task.",
                )
            return ApplicationResult(
                kind="rejected",
                message="I couldn't understand that request. Please try again.",
                data={"error": type(exc).__name__},
            )
        except Exception as exc:
            logger.exception("Planner execution failed")
            return ApplicationResult(
                kind="rejected",
                message="I couldn't understand that request. Please try again.",
                data={"error": type(exc).__name__},
            )

    async def post_async(self, shared: dict, _prep_res, exec_res):
        if isinstance(exec_res, ApplicationResult):
            shared["application_result"] = exec_res
            return "render"
        if exec_res is None:
            shared["application_result"] = ApplicationResult(
                kind="rejected",
                message="I couldn't understand that request. Please try again.",
            )
            return "render"

        shared["plan"] = exec_res
        if (
            exec_res.intent in {"edit_task", "mark_done", "delete_task", "clarify"}
            and exec_res.task_reference
        ):
            return "resolve"
        return "execute"


class ResolveTargetNode(AsyncNode):
    def __init__(self, resolver):
        super().__init__()
        self._resolver = resolver

    async def prep_async(self, shared: dict):
        return {
            "plan": shared["plan"],
            "actor_id": shared["actor_id"],
            "user_name": shared["user_name"],
            "user_timezone": shared["user_timezone"],
            "text": shared["text"],
            "channel": shared["channel"],
            "session_id": shared["session_id"],
            "trace_id": shared.get("trace_id", ""),
            "trace_context": shared.get("trace_context"),
            "llm": shared["llm"],
        }

    async def exec_async(self, payload: dict):
        plan: PlannerPlan = payload.get("plan")
        request = _request_from_shared(payload)
        if plan is None:
            raise RuntimeError("resolution context unavailable")
        if not plan.task_reference:
            return None
        return await self._resolver.resolve(request.actor_id, plan.task_reference)

    async def post_async(self, shared: dict, _prep_res, exec_res):
        shared["resolution"] = exec_res
        return "execute"


class ExecuteIntentNode(AsyncNode):
    def __init__(self, services: dict[str, object]):
        super().__init__()
        self._services = services

    async def prep_async(self, shared: dict):
        return shared

    async def exec_async(self, shared: dict):
        request = _request_from_shared(shared)
        plan: PlannerPlan = shared.get("plan")
        resolution = shared.get("resolution")
        llm = shared["llm"]
        if request is None or plan is None:
            raise RuntimeError("execution context unavailable")

        if plan.intent == "clarify":
            clarification_context = build_clarification_hint(
                shared.get("recent_clarification_context")
            )
            return ApplicationResult(
                kind="needs_clarification",
                message=(
                    plan.clarification_question
                    or clarification_context
                    or "Could you clarify that?"
                ),
                interaction=ApplicationInteraction(
                    kind="clarification",
                    choices=[
                        candidate.title
                        for candidate in getattr(resolution, "candidates", [])
                    ],
                    expected_input=plan.task_reference,
                ),
            )

        if plan.intent == "chat":
            clarification_context = build_clarification_hint(
                shared.get("recent_clarification_context")
            )
            trace_context = get_active_trace_context()
            message = await llm.complete_text(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Task Genie. Reply briefly and helpfully."
                            + (
                                f" Recent clarification context: {clarification_context}."
                                if clarification_context
                                else ""
                            )
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"{request.user_name}: {request.text}",
                    },
                ],
                api_key=request.openai_key,
                request_message=sanitize_request_message(
                    request_text=request.text,
                    history_summary=shared.get("history_summary"),
                    clarification_hint=clarification_context,
                ),
                trace_context=trace_context,
            )
            return ApplicationResult(kind="completed", message=message)

        if plan.intent in {"edit_task", "mark_done", "delete_task"} and (
            resolution is None or not getattr(resolution, "candidates", [])
        ):
            return ApplicationResult(
                kind="needs_clarification",
                message="Which task should I use?",
                interaction=ApplicationInteraction(kind="clarification"),
            )

        if getattr(resolution, "ambiguous", False):
            return ApplicationResult(
                kind="needs_clarification",
                message="I found more than one matching task. Which one did you mean?",
                interaction=ApplicationInteraction(
                    kind="clarification",
                    choices=[candidate.title for candidate in resolution.candidates],
                    expected_input=plan.task_reference,
                ),
            )

        if plan.intent == "create_task":
            task_datetime = plan.parsed_task_datetime()
            if task_datetime is None:
                return ApplicationResult(
                    kind="rejected",
                    message=(
                        "I need a date and time for that task. Please send it again with when it should be due."
                    ),
                )
            return await self._services["create_task"](
                user_id=request.actor_id,
                title=plan.task_title or request.text,
                task_datetime=task_datetime,
                description=plan.task_description,
                priority=plan.priority or "medium",
                tags=plan.tags,
            )

        if plan.intent == "edit_task":
            matched = getattr(resolution, "matched", None)
            if resolution is None or matched is None:
                return ApplicationResult(
                    kind="needs_clarification",
                    message="Which task should I use?",
                    interaction=ApplicationInteraction(kind="clarification"),
                )
            task_datetime = plan.parsed_task_datetime()
            return await self._services["edit_task"](
                user_id=request.actor_id,
                task_id=matched.task_id,
                title=plan.task_title,
                description=plan.task_description,
                task_datetime=task_datetime,
                priority=plan.priority,
                tags=plan.tags or None,
            )

        if plan.intent == "mark_done":
            matched = getattr(resolution, "matched", None)
            if resolution is None or matched is None:
                return ApplicationResult(
                    kind="needs_clarification",
                    message="Which task should I use?",
                    interaction=ApplicationInteraction(kind="clarification"),
                )
            return await self._services["mark_task_done"](
                user_id=request.actor_id,
                task_id=matched.task_id,
            )

        if plan.intent == "delete_task":
            matched = getattr(resolution, "matched", None)
            if resolution is None or matched is None:
                return ApplicationResult(
                    kind="needs_clarification",
                    message="Which task should I use?",
                    interaction=ApplicationInteraction(kind="clarification"),
                )
            return await self._services["delete_task"](
                user_id=request.actor_id,
                task_id=matched.task_id,
            )

        if plan.intent == "list_tasks":
            return await self._services["list_tasks"](
                user_id=request.actor_id,
                status=plan.status,
                limit=plan.limit or 10,
            )

        if plan.intent == "get_stats":
            return await self._services["get_task_statistics"](user_id=request.actor_id)

        return ApplicationResult(kind="completed", message="I can help with tasks.")

    async def post_async(self, shared: dict, _prep_res, exec_res):
        shared["application_result"] = exec_res
        return "render"


class RenderResponseNode(AsyncNode):
    def __init__(self, _llm=None):
        super().__init__()

    async def prep_async(self, shared: dict):
        return {"application_result": shared.get("application_result")}

    async def exec_async(self, payload):
        result = payload.get("application_result") or payload
        if isinstance(result, ConversationResponse):
            return result
        if isinstance(result, ApplicationResult):
            return ConversationResponse(
                message=result.message,
                kind=result.kind,
                interaction=result.interaction,
                data=result.data,
            )
        if isinstance(result, dict):
            message = result.get("message") or result.get("error")
            kind = result.get("kind") or (
                "completed" if result.get("success", True) else "rejected"
            )
            interaction = result.get("interaction")
            data = (
                result.get("data") if isinstance(result.get("data"), dict) else result
            )
            return ConversationResponse(
                message=message,
                kind=kind,
                interaction=interaction,
                data=data,
            )
        return ConversationResponse(message=None)

    async def post_async(self, shared: dict, _prep_res, exec_res):
        shared["response"] = exec_res
        return "persist"


class PersistHistoryNode(AsyncNode):
    def __init__(self, history: ConversationHistoryService | None = None):
        super().__init__()
        self._history = history or ConversationHistoryService()

    async def prep_async(self, shared: dict):
        return {
            "actor_id": shared["actor_id"],
            "user_name": shared["user_name"],
            "user_timezone": shared["user_timezone"],
            "text": shared["text"],
            "channel": shared["channel"],
            "session_id": shared["session_id"],
            "trace_id": shared.get("trace_id", ""),
            "response": shared["response"],
            "llm": shared["llm"],
        }

    async def exec_async(self, payload: dict):
        request = _request_from_shared(payload)
        response: ConversationResponse = payload.get("response")
        if response is None:
            raise RuntimeError("history context unavailable")
        await self._history.persist_user_turn(
            request.actor_id, request.channel, request.session_id, request.text
        )
        await self._history.persist_application_turn(
            request.actor_id, request.channel, request.session_id, response
        )
        return response

    async def post_async(self, shared: dict, _prep_res, exec_res):
        shared["response"] = exec_res
        return "default"
