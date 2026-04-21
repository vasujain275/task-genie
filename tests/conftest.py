from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_stub_modules() -> None:
    if "pydantic" not in sys.modules:
        pydantic = types.ModuleType("pydantic")

        class BaseModel:
            def __init__(self, **data: Any):
                for key, value in data.items():
                    setattr(self, key, value)

            @classmethod
            def model_rebuild(cls, *args: Any, **kwargs: Any):
                return None

        def Field(default=None, **_kwargs):
            return default

        def AliasChoices(*_choices):
            return _choices

        pydantic.BaseModel = BaseModel
        pydantic.Field = Field
        pydantic.AliasChoices = AliasChoices
        sys.modules["pydantic"] = pydantic

    if "beanie" not in sys.modules:
        beanie = types.ModuleType("beanie")

        class Document:
            @classmethod
            def model_rebuild(cls, *args: Any, **kwargs: Any):
                return None

        class Link:
            pass

        class PydanticObjectId(str):
            pass

        async def init_beanie(*args: Any, **kwargs: Any):
            return None

        beanie.Document = Document
        beanie.Link = Link
        beanie.PydanticObjectId = PydanticObjectId
        beanie.init_beanie = init_beanie
        sys.modules["beanie"] = beanie

    if "pocketflow" not in sys.modules:
        pocketflow = types.ModuleType("pocketflow")

        class AsyncNode:
            def __init__(self, *args: Any, **kwargs: Any):
                self._next = {}

            def next(self, node, label="default"):
                self._next[label] = node

        class AsyncFlow:
            def __init__(self, *args: Any, **kwargs: Any):
                self._start = None

            def start(self, node):
                self._start = node

            async def run_async(self, shared):
                node = self._start
                label = await node.post_async(
                    shared, None, await node.exec_async(await node.prep_async(shared))
                )
                while label in getattr(node, "_next", {}):
                    node = node._next[label]
                    prep = await node.prep_async(shared)
                    exec_res = await node.exec_async(prep)
                    label = await node.post_async(shared, prep, exec_res)

        pocketflow.AsyncNode = AsyncNode
        pocketflow.AsyncFlow = AsyncFlow
        sys.modules["pocketflow"] = pocketflow

    if "pocketflow_tracing" not in sys.modules:
        pocketflow_tracing = types.ModuleType("pocketflow_tracing")

        def trace_flow(*_args, **_kwargs):
            def decorator(flow_cls):
                return flow_cls

            return decorator

        pocketflow_tracing.trace_flow = trace_flow
        sys.modules["pocketflow_tracing"] = pocketflow_tracing

    if "fastapi" not in sys.modules:
        fastapi = types.ModuleType("fastapi")

        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str = ""):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class BackgroundTasks:
            def __init__(self):
                self.tasks = []

            def add_task(self, func, *args, **kwargs):
                self.tasks.append((func, args, kwargs))

        class Request:
            pass

        class FastAPI:
            def __init__(self, *args, **kwargs):
                self.state = types.SimpleNamespace()

            def add_middleware(self, *args, **kwargs):
                return None

            def get(self, *args, **kwargs):
                def decorator(func):
                    return func

                return decorator

            def post(self, *args, **kwargs):
                def decorator(func):
                    return func

                return decorator

        fastapi.FastAPI = FastAPI
        fastapi.HTTPException = HTTPException
        fastapi.BackgroundTasks = BackgroundTasks
        fastapi.Request = Request
        fastapi.status = types.SimpleNamespace(
            HTTP_400_BAD_REQUEST=400,
            HTTP_403_FORBIDDEN=403,
            HTTP_500_INTERNAL_SERVER_ERROR=500,
        )
        sys.modules["fastapi"] = fastapi

        fastapi_middleware = types.ModuleType("fastapi.middleware")
        sys.modules["fastapi.middleware"] = fastapi_middleware

        fastapi_middleware_cors = types.ModuleType("fastapi.middleware.cors")

        class CORSMiddleware:
            pass

        fastapi_middleware_cors.CORSMiddleware = CORSMiddleware
        sys.modules["fastapi.middleware.cors"] = fastapi_middleware_cors

    if "motor" not in sys.modules:
        motor = types.ModuleType("motor")
        sys.modules["motor"] = motor

    if "motor.motor_asyncio" not in sys.modules:
        motor_asyncio = types.ModuleType("motor.motor_asyncio")

        class AsyncIOMotorClient:
            def __init__(self, *args: Any, **kwargs: Any):
                self.args = args
                self.kwargs = kwargs

            def close(self):
                return None

        motor_asyncio.AsyncIOMotorClient = AsyncIOMotorClient
        sys.modules["motor.motor_asyncio"] = motor_asyncio

    if "aiogram" not in sys.modules:
        aiogram = types.ModuleType("aiogram")

        class Router:
            def message(self, *args, **kwargs):
                def decorator(func):
                    return func

                return decorator

            def callback_query(self, *args, **kwargs):
                def decorator(func):
                    return func

                return decorator

        class Command:
            def __init__(self, *_args, **_kwargs):
                pass

        class Bot:
            def __init__(self, token: str):
                self.token = token
                self.webhooks = []
                self.deleted = False
                self.session = types.SimpleNamespace(close=lambda: None)

            async def set_webhook(self, url: str, **kwargs):
                self.webhooks.append((url, kwargs))

            async def delete_webhook(self):
                self.deleted = True

        class Dispatcher:
            def __init__(self, storage=None):
                self.storage = storage
                self.routers = []

            def include_router(self, router):
                self.routers.append(router)

        class _FText:
            def startswith(self, *_args, **_kwargs):
                return self

            def __and__(self, _other):
                return self

            def __invert__(self):
                return self

        class _F:
            text = _FText()

            class _FData:
                def __eq__(self, _other):
                    return self

                def startswith(self, *_args, **_kwargs):
                    return self

            data = _FData()

        aiogram.Router = Router
        aiogram.Bot = Bot
        aiogram.Dispatcher = Dispatcher
        aiogram.F = _F()
        aiogram.types = types.ModuleType("aiogram.types")
        sys.modules["aiogram"] = aiogram

        aiogram_types = types.ModuleType("aiogram.types")

        class Message:
            pass

        class Update:
            def __init__(self, **data: Any):
                for key, value in data.items():
                    setattr(self, key, value)

        class CallbackQuery:
            pass

        class InlineKeyboardButton:
            def __init__(self, *args: Any, **kwargs: Any):
                self.args = args
                self.kwargs = kwargs

        class InlineKeyboardMarkup:
            def __init__(self, *args: Any, **kwargs: Any):
                self.args = args
                self.kwargs = kwargs

        class BotCommand:
            def __init__(self, *args: Any, **kwargs: Any):
                self.args = args
                self.kwargs = kwargs

        aiogram_types.Message = Message
        aiogram_types.Update = Update
        aiogram_types.CallbackQuery = CallbackQuery
        aiogram_types.InlineKeyboardButton = InlineKeyboardButton
        aiogram_types.InlineKeyboardMarkup = InlineKeyboardMarkup
        aiogram_types.BotCommand = BotCommand
        sys.modules["aiogram.types"] = aiogram_types
        aiogram.types = aiogram_types

        aiogram_fsm_context = types.ModuleType("aiogram.fsm.context")

        class FSMContext:
            pass

        aiogram_fsm_context.FSMContext = FSMContext
        sys.modules["aiogram.fsm.context"] = aiogram_fsm_context

        aiogram_filters = types.ModuleType("aiogram.filters")

        class StateFilter:
            def __init__(self, *_args, **_kwargs):
                pass

        aiogram_filters.StateFilter = StateFilter
        aiogram_filters.Command = Command
        sys.modules["aiogram.filters"] = aiogram_filters

        aiogram_fsm_storage = types.ModuleType("aiogram.fsm.storage")
        sys.modules["aiogram.fsm.storage"] = aiogram_fsm_storage

        aiogram_fsm_storage_redis = types.ModuleType("aiogram.fsm.storage.redis")

        class RedisStorage:
            @classmethod
            def from_url(cls, url, *args, **kwargs):
                storage = cls()
                storage.url = url
                storage.args = args
                storage.kwargs = kwargs
                return storage

        aiogram_fsm_storage_redis.RedisStorage = RedisStorage
        sys.modules["aiogram.fsm.storage.redis"] = aiogram_fsm_storage_redis

        aiogram_fsm_state = types.ModuleType("aiogram.fsm.state")

        class State:
            pass

        class StatesGroup:
            pass

        aiogram_fsm_state.State = State
        aiogram_fsm_state.StatesGroup = StatesGroup
        sys.modules["aiogram.fsm.state"] = aiogram_fsm_state

    app_utils_logger = types.ModuleType("app.utils.logger")

    def setup_logger(_name: str):
        import logging

        return logging.getLogger(_name)

    app_utils_logger.setup_logger = setup_logger
    sys.modules["app.utils.logger"] = app_utils_logger

    app_utils_security = types.ModuleType("app.utils.security")
    app_utils_security.encrypt_api_key = lambda value: value
    app_utils_security.decrypt_api_key = lambda value: value
    sys.modules["app.utils.security"] = app_utils_security

    app_models_conversation_turn = types.ModuleType("app.models.conversation_turn")
    app_models_conversation_turn.CONVERSATION_TURN_RETENTION_DAYS = 14

    class ConversationTurn:
        def __init__(self, **data: Any):
            for key, value in data.items():
                setattr(self, key, value)

        @classmethod
        def model_rebuild(cls, *args: Any, **kwargs: Any):
            return None

        @classmethod
        async def create_turn(cls, **data: Any):
            return cls(**data)

        @classmethod
        async def recent_for_session(cls, *args: Any, **kwargs: Any):
            return []

    app_models_conversation_turn.ConversationTurn = ConversationTurn
    sys.modules["app.models.conversation_turn"] = app_models_conversation_turn


_install_stub_modules()
