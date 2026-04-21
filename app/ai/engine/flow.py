from __future__ import annotations

from dataclasses import dataclass

try:
    from pocketflow import AsyncFlow
except Exception:  # pragma: no cover - test/runtime fallback

    class AsyncFlow:
        def __init__(self, *args, **kwargs):
            self._start = None

        def start(self, node):
            self._start = node

        async def run_async(self, shared):
            node = self._start
            while node is not None:
                prep = await node.prep_async(shared)
                exec_res = await node.exec_async(prep)
                label = await node.post_async(shared, prep, exec_res)
                node = getattr(node, "_next", {}).get(label)


try:
    from pocketflow_tracing import trace_flow
except Exception:  # pragma: no cover - test/runtime fallback

    def trace_flow(*_args, **_kwargs):
        def decorator(flow_cls):
            return flow_cls

        return decorator


from app.ai.engine.llm import LiteLLMAdapter
from app.ai.engine.history import ConversationHistoryService
from app.ai.engine.tracing import (
    request_trace,
    normalize_session_id,
    normalize_trace_id,
    sanitize_request_state,
    tracing_enabled,
)
from app.ai.engine.nodes import (
    ExecuteIntentNode,
    LoadRequestNode,
    PersistHistoryNode,
    PlanIntentNode,
    RenderResponseNode,
    ResolveTargetNode,
)
from app.ai.engine.resolver import TaskReferenceResolver
from app.ai.services import task_services
from app.application.contracts import ConversationRequest, ConversationResponse


@dataclass
class ConversationRuntimeContext:
    request: ConversationRequest
    recent_turns: list | None = None
    history_summary: str | None = None
    recent_clarification_context: object | None = None
    clarification_hint: str | None = None
    current_datetime: str | None = None
    timezone_warning: str | None = None
    plan: object | None = None
    resolution: object | None = None
    application_result: object | None = None
    response: object | None = None
    trace_metadata: dict | None = None
    trace_id: str | None = None


@trace_flow()
@dataclass
class PocketFlowConversationFlow:
    llm: LiteLLMAdapter
    resolver: TaskReferenceResolver
    history: ConversationHistoryService
    flow: AsyncFlow
    load_request: LoadRequestNode
    plan_intent: PlanIntentNode
    resolve_target: ResolveTargetNode
    execute_intent: ExecuteIntentNode
    render_response: RenderResponseNode
    persist_history: PersistHistoryNode
    _current_request: ConversationRequest | None = None
    _runtime: ConversationRuntimeContext | None = None

    @classmethod
    def build(cls, model: str | None = None) -> "PocketFlowConversationFlow":
        if model is None:
            from app.config import settings

            model = settings.MODEL

        llm = LiteLLMAdapter(model)
        history = ConversationHistoryService()
        resolver = TaskReferenceResolver(_load_user_tasks)
        load_request = LoadRequestNode(history)
        plan_intent = PlanIntentNode(llm)
        resolve_target = ResolveTargetNode(resolver)
        execute_intent = ExecuteIntentNode(
            {
                "create_task": task_services.create_task,
                "edit_task": task_services.edit_task,
                "mark_task_done": task_services.mark_task_done,
                "delete_task": task_services.delete_task,
                "list_tasks": task_services.list_tasks,
                "get_task_statistics": task_services.get_task_statistics,
            }
        )
        render_response = RenderResponseNode(llm)
        persist_history = PersistHistoryNode(history)

        flow = AsyncFlow()
        flow.start(load_request)
        load_request.next(plan_intent)
        plan_intent.next(resolve_target, "resolve")
        plan_intent.next(execute_intent, "execute")
        plan_intent.next(render_response, "render")
        resolve_target.next(execute_intent, "execute")
        execute_intent.next(render_response, "render")
        render_response.next(persist_history, "persist")
        flow_obj = cls(
            llm=llm,
            resolver=resolver,
            history=history,
            flow=flow,
            load_request=load_request,
            plan_intent=plan_intent,
            resolve_target=resolve_target,
            execute_intent=execute_intent,
            render_response=render_response,
            persist_history=persist_history,
        )
        return flow_obj

    async def generate(self, request: ConversationRequest) -> ConversationResponse:
        self._current_request = request
        self._runtime = ConversationRuntimeContext(request=request)
        try:
            session_id = normalize_session_id(
                request.channel, request.session_id, request.actor_id
            )
            trace_id = normalize_trace_id(
                trace_id=getattr(request, "trace_id", ""),
                session_id=session_id,
                user_id=request.actor_id,
                channel=request.channel,
            )
            bind_api_key = getattr(self.llm, "bind_api_key", None)
            bound_llm = (
                bind_api_key(request.openai_key) if callable(bind_api_key) else self.llm
            )
            self._runtime.trace_metadata = {
                "channel": request.channel,
                "model": getattr(self.llm, "model", None),
                "session_id": session_id,
                "user_id": str(request.actor_id),
                "trace_id": trace_id,
            }
            self._runtime.trace_id = trace_id
            safe_state: dict = {
                "request_meta": sanitize_request_state(
                    trace_id=trace_id,
                    session_id=session_id,
                    user_id=str(request.actor_id),
                    channel=request.channel,
                    model=getattr(self.llm, "model", "unknown"),
                    request_text=request.text,
                    recent_turns_count=0,
                    history_summary=None,
                ),
                "llm": bound_llm,
                "trace_meta": self._runtime.trace_metadata,
                "actor_id": request.actor_id,
                "user_name": request.user_name,
                "user_timezone": request.user_timezone,
                "text": request.text,
                "channel": request.channel,
                "session_id": session_id,
                "trace_id": trace_id,
            }
            if tracing_enabled():
                async with request_trace(
                    name="conversation.generate",
                    trace_id=trace_id,
                    session_id=session_id,
                    user_id=str(request.actor_id),
                    metadata=self._runtime.trace_metadata,
                ):
                    await self.flow.run_async(safe_state)
            else:
                await self.flow.run_async(safe_state)
            response = safe_state.get("response")
            if isinstance(response, ConversationResponse):
                return response
            if isinstance(response, dict):
                return ConversationResponse(
                    message=response.get("message") or response.get("error"),
                    kind=response.get("kind", "completed"),
                    interaction=response.get("interaction"),
                    data=response.get("data")
                    if isinstance(response.get("data"), dict)
                    else response,
                )
            return ConversationResponse(message=getattr(response, "message", None))
        finally:
            self._current_request = None
            self._runtime = None


async def _load_user_tasks(user_id: int):
    from app.models.task import Task
    from app.models.user import User

    user = await User.get_by_telegram_id(user_id)
    if not user:
        return []

    query = Task.find(Task.user.id == user.id)
    return await query.to_list()


def build_conversation_flow(model: str | None = None) -> PocketFlowConversationFlow:
    return PocketFlowConversationFlow.build(model=model)
