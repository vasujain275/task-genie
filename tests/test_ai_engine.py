from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime

import pytest

from app.ai.engine.flow import PocketFlowConversationFlow
from app.ai.engine.history import ConversationHistoryService
from app.ai.engine.nodes import (
    ExecuteIntentNode,
    PlanIntentNode,
    RenderResponseNode,
)
from app.ai.engine.resolver import TaskReferenceResolver
from app.ai.engine.schemas import PlannerPlan
from app.application.contracts import ConversationRequest


@dataclass
class FakeTurn:
    actor_id: int
    channel: str
    session_id: str
    role: str
    content: str
    kind: str | None = None
    interaction_kind: str | None = None
    choices: list[str] | None = None
    expected_input: str | None = None


@dataclass
class FakeTask:
    id: str
    title: str
    status: str = "pending"


class FakeLLM:
    def __init__(self, plan=None, chat_message="chat ok"):
        self.plan = plan
        self.chat_message = chat_message
        self.json_calls = []
        self.text_calls = []
        self._api_key = None

    async def complete_json(self, *, messages, api_key, schema, **kwargs):
        self.json_calls.append(
            {"messages": messages, "api_key": api_key, "schema": schema, **kwargs}
        )
        return self.plan

    async def complete_text(self, *, messages, api_key, temperature=0.2, **kwargs):
        self.text_calls.append(
            {
                "messages": messages,
                "api_key": api_key,
                "temperature": temperature,
                **kwargs,
            }
        )
        return self.chat_message

    @property
    def model(self):
        return "test-model"


class BrokenLLM(FakeLLM):
    async def complete_json(self, *, messages, api_key, schema, **kwargs):
        self.json_calls.append(
            {"messages": messages, "api_key": api_key, "schema": schema, **kwargs}
        )
        return {"intent": "create_task"}


def build_flow(llm, resolver, services):
    flow = PocketFlowConversationFlow.build(model="test-model")
    flow.llm = llm
    flow.resolver = resolver
    flow.history = ConversationHistoryService()
    flow.load_request._history = flow.history
    flow.plan_intent._llm = llm
    flow.resolve_target._resolver = resolver
    flow.execute_intent._services = services
    flow.render_response._llm = llm
    return flow


def _patch_history(monkeypatch, recent_turns=None):
    recent_turns = recent_turns or []

    async def recent_for_session(**_kwargs):
        return recent_turns

    async def create_turn(**kwargs):
        return FakeTurn(**kwargs)

    from app.models import conversation_turn

    monkeypatch.setattr(
        conversation_turn.ConversationTurn, "recent_for_session", recent_for_session
    )
    monkeypatch.setattr(conversation_turn.ConversationTurn, "create_turn", create_turn)


def test_history_load_save_behavior(monkeypatch):
    saved = []
    stored = [FakeTurn(1, "telegram", "s", "user", "hi")]

    async def recent_for_session(**kwargs):
        assert kwargs == {
            "actor_id": 1,
            "channel": "telegram",
            "session_id": "s",
            "limit": 12,
        }
        return stored

    async def create_turn(**kwargs):
        saved.append(kwargs)
        return FakeTurn(**kwargs)

    from app.models import conversation_turn

    monkeypatch.setattr(
        conversation_turn.ConversationTurn, "recent_for_session", recent_for_session
    )
    monkeypatch.setattr(conversation_turn.ConversationTurn, "create_turn", create_turn)

    service = ConversationHistoryService()
    turns = asyncio.run(service.load_recent_turns(1, "telegram", "s"))
    assert turns == stored

    asyncio.run(service.persist_user_turn(1, "telegram", "s", "hello"))
    assert saved[0] == {
        "actor_id": 1,
        "channel": "telegram",
        "session_id": "s",
        "role": "user",
        "content": "hello",
    }
    assert saved[0]["role"] == "user"


def test_history_persists_assistant_interaction_metadata(monkeypatch):
    saved = []

    async def create_turn(**kwargs):
        saved.append(kwargs)
        return FakeTurn(**kwargs)

    from app.models import conversation_turn

    monkeypatch.setattr(conversation_turn.ConversationTurn, "create_turn", create_turn)

    service = ConversationHistoryService()
    response = type(
        "Response",
        (),
        {
            "message": "Which task?",
            "kind": "needs_clarification",
            "interaction": type(
                "Interaction",
                (),
                {
                    "kind": "clarification",
                    "choices": ["Call mom"],
                    "expected_input": "call mom",
                },
            )(),
        },
    )()

    asyncio.run(service.persist_application_turn(1, "telegram", "s", response))

    assert saved[0]["role"] == "assistant"
    assert saved[0]["kind"] == "needs_clarification"
    assert saved[0]["interaction_kind"] == "clarification"
    assert saved[0]["choices"] == ["Call mom"]
    assert saved[0]["expected_input"] == "call mom"


def test_history_scopes_missing_session_by_actor_and_channel(monkeypatch):
    captured = []

    async def recent_for_session(**kwargs):
        captured.append(kwargs)
        return []

    async def create_turn(**kwargs):
        captured.append(kwargs)
        return FakeTurn(**kwargs)

    from app.models import conversation_turn

    monkeypatch.setattr(
        conversation_turn.ConversationTurn, "recent_for_session", recent_for_session
    )
    monkeypatch.setattr(conversation_turn.ConversationTurn, "create_turn", create_turn)

    service = ConversationHistoryService()
    asyncio.run(service.load_recent_turns(7, "telegram", ""))
    asyncio.run(service.persist_user_turn(7, "telegram", "", "hello"))

    assert captured[0]["session_id"] == "telegram:7"
    assert captured[1]["session_id"] == "telegram:7"
    assert captured[1]["actor_id"] == 7
    assert captured[1]["channel"] == "telegram"


def test_history_bounded_last_12_turns(monkeypatch):
    captured = {}

    async def recent_for_session(**kwargs):
        captured.update(kwargs)
        return []

    from app.models import conversation_turn

    monkeypatch.setattr(
        conversation_turn.ConversationTurn, "recent_for_session", recent_for_session
    )

    service = ConversationHistoryService(default_limit=12)
    asyncio.run(service.load_recent_turns(7, "telegram", "session-x", limit=None))
    assert captured["limit"] == 12


def test_history_session_scoping(monkeypatch):
    captured = []

    async def recent_for_session(**kwargs):
        captured.append(kwargs)
        return []

    from app.models import conversation_turn

    monkeypatch.setattr(
        conversation_turn.ConversationTurn, "recent_for_session", recent_for_session
    )

    service = ConversationHistoryService()
    asyncio.run(service.load_recent_turns(1, "telegram", "session-a"))
    asyncio.run(service.load_recent_turns(1, "telegram", "session-b"))

    assert captured[0]["session_id"] != captured[1]["session_id"]


def test_history_clarification_context_survives(monkeypatch):
    turns = [
        FakeTurn(1, "telegram", "s", "user", "edit it"),
        FakeTurn(
            1,
            "telegram",
            "s",
            "assistant",
            "Which task?",
            kind="needs_clarification",
            interaction_kind="clarification",
            choices=["Call mom"],
            expected_input="call mom",
        ),
        FakeTurn(1, "telegram", "s", "user", "the first one"),
        FakeTurn(
            1,
            "telegram",
            "s",
            "assistant",
            "Some later reply",
            kind="completed",
        ),
    ]

    async def recent_for_session(**_kwargs):
        return turns

    from app.models import conversation_turn

    monkeypatch.setattr(
        conversation_turn.ConversationTurn, "recent_for_session", recent_for_session
    )

    llm = FakeLLM(plan={"intent": "chat"}, chat_message="Okay")
    flow = build_flow(
        llm,
        TaskReferenceResolver(lambda _user_id: []),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    asyncio.run(
        flow.generate(
            ConversationRequest(1, "Ana", "UTC", "yes", "encrypted", "telegram", "s")
        )
    )
    assert llm.text_calls
    assert "clarification" in llm.text_calls[0]["messages"][0]["content"].lower()


def test_execute_intent_requires_matched_resolution_for_mutations():
    llm = FakeLLM(plan={"intent": "chat"})
    services = {
        "create_task": lambda **_kwargs: None,
        "edit_task": lambda **_kwargs: None,
        "mark_task_done": lambda **_kwargs: None,
        "delete_task": lambda **_kwargs: None,
        "list_tasks": lambda **_kwargs: None,
        "get_task_statistics": lambda **_kwargs: None,
    }
    node = ExecuteIntentNode(services)

    shared = {
        "actor_id": 1,
        "user_name": "Ana",
        "user_timezone": "UTC",
        "text": "edit it",
        "channel": "telegram",
        "session_id": "s",
        "llm": llm,
        "plan": PlannerPlan(intent="edit_task", task_reference="call mom"),
        "resolution": type("Resolution", (), {"candidates": []})(),
    }

    result = asyncio.run(node.exec_async(shared))

    assert result.kind == "needs_clarification"
    assert result.message == "Which task should I use?"


def test_history_render_turns_does_not_duplicate_clarification_text():
    service = ConversationHistoryService()
    turns = [
        FakeTurn(
            1,
            "telegram",
            "s",
            "assistant",
            "Which task?",
            kind="needs_clarification",
            choices=["Call mom"],
            expected_input="call mom",
        )
    ]

    rendered = service.render_turns(turns)

    assert rendered == "Assistant: Which task? (Choices: Call mom | Expected: call mom)"


def test_history_does_not_persist_sensitive_keys(monkeypatch):
    captured = []

    async def create_turn(**kwargs):
        captured.append(kwargs)
        return FakeTurn(**kwargs)

    from app.models import conversation_turn

    monkeypatch.setattr(conversation_turn.ConversationTurn, "create_turn", create_turn)

    service = ConversationHistoryService()
    asyncio.run(service.persist_user_turn(1, "telegram", "s", "hello"))
    assert "openai_key" not in captured[0]


def test_planner_schema_validation():
    with pytest.raises(ValueError):
        PlannerPlan.model_validate({"intent": "create_task"})

    with pytest.raises(ValueError):
        PlannerPlan.model_validate({"intent": "clarify"})

    with pytest.raises(ValueError):
        PlannerPlan.model_validate({"intent": "edit_task"})


def test_load_user_tasks_does_not_apply_artificial_cap(monkeypatch):
    from app.ai.engine import flow as flow_module

    class FakeQuery:
        def __init__(self):
            self.limit_called = False

        def limit(self, _value):
            self.limit_called = True
            raise AssertionError("limit should not be called")

        async def to_list(self):
            return [FakeTask(str(i), f"Task {i}") for i in range(25)]

    class FakeTaskModel:
        user = type("UserRef", (), {"id": 7})()

        @classmethod
        def find(cls, *_args, **_kwargs):
            return FakeQuery()

    async def get_user(_user_id):
        return type("User", (), {"id": 7})()

    monkeypatch.setattr("app.models.user.User.get_by_telegram_id", get_user)
    monkeypatch.setattr("app.models.task.Task", FakeTaskModel, raising=False)

    tasks = asyncio.run(flow_module._load_user_tasks(101))

    assert len(tasks) == 25
    assert not hasattr(tasks, "limit")


def test_task_reference_resolver_detects_ambiguity():
    async def query(_user_id):
        return [FakeTask("1", "Call mom"), FakeTask("2", "Call mom")]

    resolver = TaskReferenceResolver(query)
    result = asyncio.run(resolver.resolve(101, "call mom"))

    assert result.matched is None
    assert result.ambiguous is True
    assert len(result.candidates) == 2


def test_flow_create_task_path():
    llm = FakeLLM(
        plan={
            "intent": "create_task",
            "task_title": "Call mom",
            "task_datetime": "2026-04-16T09:00:00+00:00",
            "priority": "medium",
            "tags": ["personal"],
        }
    )

    async def query(_user_id):
        return []

    captured = {}

    async def create_task(**kwargs):
        captured.update(kwargs)
        return {"success": True, "message": "✓ 'Call mom' created"}

    flow = build_flow(
        llm,
        TaskReferenceResolver(query),
        {
            "create_task": create_task,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    result = asyncio.run(
        flow.generate(
            ConversationRequest(101, "Ana", "UTC", "Create a task", "encrypted")
        )
    )

    assert result.message == "✓ 'Call mom' created"
    assert captured["title"] == "Call mom"
    assert captured["task_datetime"] == datetime.fromisoformat(
        "2026-04-16T09:00:00+00:00"
    )


def test_flow_rejects_create_task_without_datetime():
    llm = FakeLLM(
        plan={
            "intent": "create_task",
            "task_title": "Call mom",
        }
    )

    flow = build_flow(
        llm,
        TaskReferenceResolver(lambda _user_id: []),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    result = asyncio.run(
        flow.generate(
            ConversationRequest(101, "Ana", "UTC", "Create a task", "encrypted")
        )
    )

    assert result.kind == "rejected"
    assert "date and time" in result.message.lower()


def test_flow_clarification_path():
    llm = FakeLLM(
        plan={
            "intent": "clarify",
            "task_reference": "call mom",
            "clarification_question": "Which task did you mean?",
        }
    )

    async def query(_user_id):
        return [FakeTask("1", "Call mom"), FakeTask("2", "Call mom")]

    flow = build_flow(
        llm,
        TaskReferenceResolver(query),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    result = asyncio.run(
        flow.generate(
            ConversationRequest(101, "Ana", "UTC", "edit call mom", "encrypted")
        )
    )

    assert result.kind == "needs_clarification"
    assert "Which task" in result.message


def test_flow_chat_path():
    llm = FakeLLM(plan={"intent": "chat"}, chat_message="Sure.")

    async def query(_user_id):
        return []

    flow = build_flow(
        llm,
        TaskReferenceResolver(query),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    result = asyncio.run(
        flow.generate(ConversationRequest(101, "Ana", "UTC", "hello", "encrypted"))
    )

    assert result.message == "Sure."
    assert llm.text_calls


@pytest.mark.parametrize(
    "intent,service_name,service_result,expected_kwargs",
    [
        (
            "edit_task",
            "edit_task",
            {"success": True, "message": "updated"},
            {
                "task_id": "1",
                "title": "New title",
                "description": "New desc",
                "task_datetime": None,
                "priority": None,
                "tags": None,
            },
        ),
        (
            "mark_done",
            "mark_task_done",
            {"success": True, "message": "done"},
            {"task_id": "1"},
        ),
        (
            "delete_task",
            "delete_task",
            {"success": True, "message": "deleted"},
            {"task_id": "1"},
        ),
        (
            "list_tasks",
            "list_tasks",
            {"success": True, "message": "1 task", "count": 1},
            {"status": "done", "limit": 5},
        ),
        (
            "get_stats",
            "get_task_statistics",
            {"success": True, "message": "stats"},
            {},
        ),
    ],
)
def test_flow_executes_task_branches(
    intent, service_name, service_result, expected_kwargs
):
    llm = FakeLLM(
        plan={
            "intent": intent,
            "task_reference": "1",
            "status": "done",
            "limit": 5,
            "task_title": "New title",
            "task_description": "New desc",
        }
    )

    async def query(_user_id):
        return [FakeTask("1", "Call mom")]

    captured = {}

    async def service(**kwargs):
        captured.update(kwargs)
        return service_result

    services = {
        "create_task": lambda **_kwargs: None,
        "edit_task": lambda **_kwargs: None,
        "mark_task_done": lambda **_kwargs: None,
        "delete_task": lambda **_kwargs: None,
        "list_tasks": lambda **_kwargs: None,
        "get_task_statistics": lambda **_kwargs: None,
    }
    services[service_name] = service

    flow = build_flow(llm, TaskReferenceResolver(query), services)

    result = asyncio.run(
        flow.generate(ConversationRequest(101, "Ana", "UTC", "hi", "encrypted"))
    )

    assert result.message == service_result["message"]
    assert captured == {"user_id": 101, **expected_kwargs}


def test_flow_clarification_choices_propagate():
    llm = FakeLLM(
        plan={
            "intent": "clarify",
            "task_reference": "call mom",
            "clarification_question": "Which task?",
        }
    )

    async def query(_user_id):
        return [FakeTask("1", "Call mom"), FakeTask("2", "Call mom")]

    flow = build_flow(
        llm,
        TaskReferenceResolver(query),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    result = asyncio.run(
        flow.generate(ConversationRequest(101, "Ana", "UTC", "edit", "encrypted"))
    )

    assert result.interaction.choices == ["Call mom", "Call mom"]


def test_flow_rejects_malformed_planner_output():
    llm = BrokenLLM()

    async def query(_user_id):
        return []

    flow = build_flow(
        llm,
        TaskReferenceResolver(query),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    result = asyncio.run(
        flow.generate(ConversationRequest(101, "Ana", "UTC", "hi", "encrypted"))
    )

    assert result.kind == "rejected"
    assert "couldn't understand" in result.message


def test_flow_rejects_create_task_without_datetime_message():
    llm = FakeLLM(plan={"intent": "create_task", "task_title": "Call mom"})

    flow = build_flow(
        llm,
        TaskReferenceResolver(lambda _user_id: []),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    result = asyncio.run(
        flow.generate(ConversationRequest(101, "Ana", "UTC", "hi", "encrypted"))
    )

    assert result.kind == "rejected"
    assert "date and time" in result.message.lower()


def test_plan_intent_logs_and_rejects_on_planner_exception(monkeypatch):
    class ExplodingLLM(FakeLLM):
        async def complete_json(self, *, messages, api_key, schema, **kwargs):
            raise RuntimeError("planner boom")

    llm = ExplodingLLM()
    node = PlanIntentNode(llm)

    result = asyncio.run(
        node.exec_async(
            {
                "request": ConversationRequest(1, "Ana", "UTC", "hi", "key"),
                "history_summary": None,
                "clarification_hint": None,
                "current_datetime": None,
            }
        )
    )

    assert result.kind == "rejected"
    assert result.data == {"error": "RuntimeError"}


def test_flow_invalid_timezone_falls_back_to_utc():
    llm = FakeLLM(plan={"intent": "chat"}, chat_message="Sure.")

    async def query(_user_id):
        return []

    flow = build_flow(
        llm,
        TaskReferenceResolver(query),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    result = asyncio.run(
        flow.generate(
            ConversationRequest(101, "Ana", "Invalid/Timezone", "hello", "encrypted")
        )
    )

    assert result.message == "Sure."


def test_render_response_preserves_kind_interaction_and_data():
    llm = FakeLLM(plan={"intent": "chat"})
    node = RenderResponseNode(llm)
    interaction = type(
        "Interaction",
        (),
        {"kind": "clarification", "choices": ["One"], "expected_input": "one"},
    )()

    result = asyncio.run(
        node.exec_async(
            {
                "application_result": {
                    "message": None,
                    "kind": "needs_clarification",
                    "interaction": interaction,
                    "data": {"hint": "choose one"},
                },
            }
        )
    )

    assert result.kind == "needs_clarification"
    assert result.interaction.kind == "clarification"
    assert result.data == {"hint": "choose one"}


def test_flow_generate_preserves_dict_fallback_payload():
    llm = FakeLLM(plan={"intent": "chat"}, chat_message="unused")

    async def query(_user_id):
        return []

    flow = build_flow(
        llm,
        TaskReferenceResolver(query),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    async def run_async(shared):
        shared["response"] = {
            "message": "Need more info",
            "kind": "needs_clarification",
            "interaction": type(
                "Interaction",
                (),
                {"kind": "clarification", "choices": ["A"], "expected_input": "x"},
            )(),
            "data": {"hint": "pick A"},
        }

    flow.flow.run_async = run_async  # type: ignore[method-assign]

    result = asyncio.run(
        flow.generate(ConversationRequest(101, "Ana", "UTC", "hi", "encrypted"))
    )

    assert result.kind == "needs_clarification"
    assert result.message == "Need more info"
    assert result.interaction.kind == "clarification"
    assert result.data == {"hint": "pick A"}


def test_flow_smoke_persists_turns_through_real_graph(monkeypatch):
    saved = []

    async def recent_for_session(**_kwargs):
        return [FakeTurn(101, "telegram", "telegram:101", "user", "yesterday")]

    async def create_turn(**kwargs):
        saved.append(kwargs)
        return FakeTurn(**kwargs)

    from app.models import conversation_turn

    monkeypatch.setattr(
        conversation_turn.ConversationTurn, "recent_for_session", recent_for_session
    )
    monkeypatch.setattr(conversation_turn.ConversationTurn, "create_turn", create_turn)

    llm = FakeLLM(
        plan={
            "intent": "clarify",
            "task_reference": "call mom",
            "clarification_question": "Which task?",
        }
    )

    async def query(_user_id):
        return [FakeTask("1", "Call mom")]

    flow = build_flow(
        llm,
        TaskReferenceResolver(query),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    result = asyncio.run(
        flow.generate(
            ConversationRequest(101, "Ana", "UTC", "edit call mom", "encrypted")
        )
    )

    assert result.kind == "needs_clarification"
    assert result.message == "Which task?"
    assert [entry["role"] for entry in saved] == ["user", "assistant"]
    assert saved[1]["kind"] == "needs_clarification"
    assert saved[1]["interaction_kind"] == "clarification"


def test_flow_generates_non_empty_trace_and_propagates_ids(monkeypatch):
    captured = {}

    class FakeSpan:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

    class FakeClient:
        def span(self, **kwargs):
            captured["span"] = kwargs
            return FakeSpan()

    from app.ai.engine import tracing
    from app.ai.engine import flow as flow_mod

    monkeypatch.setattr(tracing, "tracing_enabled", lambda: True)
    monkeypatch.setattr(tracing, "get_trace_client", lambda: FakeClient())
    monkeypatch.setattr(flow_mod, "tracing_enabled", lambda: True)
    tracing._trace_client = None

    llm = FakeLLM(plan={"intent": "chat"}, chat_message="hello")

    async def query(_user_id):
        return []

    flow = build_flow(
        llm,
        TaskReferenceResolver(query),
        {
            "create_task": lambda **_kwargs: None,
            "edit_task": lambda **_kwargs: None,
            "mark_task_done": lambda **_kwargs: None,
            "delete_task": lambda **_kwargs: None,
            "list_tasks": lambda **_kwargs: None,
            "get_task_statistics": lambda **_kwargs: None,
        },
    )

    asyncio.run(
        flow.generate(
            ConversationRequest(7, "Ana", "UTC", "hi", "encrypted", trace_id="")
        )
    )

    assert captured["span"]["trace_id"] == "telegram:7"
    assert captured["span"]["session_id"] == "telegram:7"
    assert captured["span"]["user_id"] == "7"
    assert captured["span"]["metadata"]["trace_id"] == "telegram:7"
    assert llm.text_calls[0]["request_message"]["request_text_length"] == 2


def test_flow_trace_gating_matches_settings(monkeypatch):
    from app.ai.engine import tracing

    monkeypatch.setattr(tracing.settings, "TRACING_ENABLED", False)
    monkeypatch.setattr(tracing.settings, "LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_SECRET_KEY", "")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_HOST", "")
    assert tracing.tracing_enabled() is False

    monkeypatch.setattr(tracing.settings, "TRACING_ENABLED", True)
    monkeypatch.setattr(tracing.settings, "LANGFUSE_PUBLIC_KEY", "pub")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_SECRET_KEY", "sec")
    monkeypatch.setattr(tracing.settings, "LANGFUSE_HOST", "https://cloud.langfuse.com")
    assert tracing.tracing_enabled() is True
