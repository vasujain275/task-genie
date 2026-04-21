# PocketFlow Migration Plan

## Goal

Fully replace LangGraph, LangChain, and LangSmith with a maintainable, channel-agnostic architecture built around:

- PocketFlow for orchestration
- LiteLLM for LLM access
- pocketflow-tracing + Langfuse for tracing
- clean application/domain boundaries
- Telegram as an adapter only

This migration should also decouple the Telegram interface from the AI and application core so future interfaces like mobile and web can reuse the same logic cleanly.

---

## Final Decisions

### Product / rollout

- Full hard swap from LangGraph to PocketFlow
- Deep redesign allowed
- Direct rollout is acceptable because project is still early-stage
- Maintainability is top priority
- Behavior can improve when it benefits the project

### AI / orchestration

- PocketFlow latest stable docs as target
- Deterministic workflow preferred over a generic agent loop
- LiteLLM will be the only LLM integration layer
- OpenAI-only support first, routed through LiteLLM
- Remove all LangChain / LangGraph / LangSmith runtime pieces

### Memory / conversation behavior

- Persist short-term conversation history across restarts
- Ambiguous task references must always ask the user
- Core task models should stay unless a schema change becomes clearly necessary
- Add conversation history persistence if needed for short-term context

### Architecture / decoupling

- Application service API is the primary boundary
- Core returns application result objects, not Telegram or HTTP DTOs
- Minimal cross-channel interaction model now
- Thin session/auth seam now, full auth later
- Telegram-specific UI behavior stays in the Telegram adapter
- Same core should support future chat and structured form flows

### Observability

- Use `pocketflow-tracing`
- Use Langfuse as tracing backend
- Avoid tracing decrypted secrets or sensitive raw payloads

---

## Current-State Findings

## What exists today

- `app/ai/graph/agent.py` contains a custom LangGraph workflow
- `app/ai/tools/task_tools.py` contains LangChain `@tool` functions for task/reminder operations
- `app/bot/handlers/conversation.py` directly invokes the LangGraph agent and parses LangChain message objects
- `app/config.py` contains LangChain / LangSmith configuration
- `app/models/` contains Beanie models for `User`, `Task`, and `Reminder`
- Telegram bot flow is implemented with Aiogram + FastAPI webhook handling

## Important gaps / mismatches

- Current code is not really a rich looping agent; it is effectively a one-pass route to tools or final response
- Current bot layer is tightly coupled to LangChain / LangGraph response types
- README claims behavior not fully matched by the current implementation
- Current conversation memory is not clearly aligned with claimed persistence behavior
- There is no meaningful automated test coverage yet

---

## Target Architecture

## High-level design

```text
Interfaces
  └── Telegram adapter

Application
  ├── use-case services
  ├── request/result contracts
  └── channel-agnostic interaction model

AI Orchestration
  ├── PocketFlow workflow
  ├── LiteLLM adapter
  ├── resolver/history/planner
  └── tracing hooks

Domain
  ├── task/reminder/user business logic
  └── domain rules and exceptions

Infrastructure
  ├── Beanie/Mongo persistence
  ├── encryption
  ├── tracing integration
  └── scheduler/runtime wiring
```

## Design rules

1. Telegram must not know PocketFlow, LiteLLM, prompts, or domain internals.
2. Application layer must not return Telegram-specific response objects.
3. Domain logic must not depend on Telegram, PocketFlow, or LiteLLM.
4. PocketFlow must orchestrate the flow, not become the persistence model.
5. Mongo remains the source of truth for business data.

---

## Request / Response Boundary

## RequestContext

Create a channel-agnostic request context used by every interface:

- `actor_id`
- `channel`
- `session_id`
- `timezone`
- `trace_id`
- optional `locale`

This prevents Telegram-specific identity/session assumptions from leaking into the core.

## ApplicationResult

Core services should return typed application result objects, not raw domain models and not transport DTOs.

Suggested shape:

- `kind`
- `message`
- `interaction`
- `data`

Examples of result kinds:

- `completed`
- `needs_clarification`
- `rejected`
- `task_list`
- `task_mutation_result`
- `stats_result`

## Minimal interaction model

Do not build a full generic widget/action framework yet.

Support only what is needed now:

- completion state
- clarification state
- optional choices
- optional expected next input

Telegram can map these to inline keyboards and markdown.
Future mobile/web interfaces can map them to buttons, cards, or forms.

---

## PocketFlow Workflow Design

## Recommended execution model

Use a deterministic PocketFlow workflow with limited branching.

Avoid a generic always-looping agent.

## Conversation flow

Per incoming user message:

1. load request context
2. load short-term history
3. load user profile and timezone
4. plan intent with structured LiteLLM output
5. resolve task references in code
6. if ambiguous, return clarification result
7. execute domain operation in code
8. render final response
9. persist conversation turn/history

## Intent set

Initial supported intents:

- `chat`
- `create_task`
- `edit_task`
- `mark_done`
- `delete_task`
- `list_tasks`
- `get_stats`
- `clarify`

## Why this shape

- bounded problem domain
- more testable than generic tool-calling agent design
- easier to reason about than hidden graph state + tool messages
- better fit for multi-interface reuse

---

## Memory Strategy

## Recommendation

Persist short-term history explicitly outside PocketFlow.

Do not recreate LangGraph checkpoint semantics.

## Suggested persistence

Add a `ConversationTurn` model or equivalent history store:

- actor/channel/session scoped
- bounded recent history only
- enough to survive restarts
- timestamps stored in UTC

## What should persist

- recent turns
- clarification state if needed
- assistant output summaries if useful

## What should not persist

- decrypted API keys
- PocketFlow internal node state
- sensitive tracing-only payloads

---

## Domain and Service Refactor

## Replace LangChain tools with plain services

Refactor current logic from `app/ai/tools/task_tools.py` into plain async services.

Recommended services:

- `ConversationService`
- `TaskService`
- `TaskQueryService`
- `TaskReferenceResolver`
- `ConversationHistoryService`

## Domain responsibilities

Domain / application logic should own:

- task creation/edit/delete/mark done
- reminder creation logic
- task querying/statistics
- reference resolution
- validation rules
- clarification requirements

PocketFlow should call these services; it should not contain core business behavior inline.

---

## Telegram Decoupling Strategy

## Telegram adapter responsibilities

- parse updates
- map Telegram update into `RequestContext`
- call application services
- render `ApplicationResult`
- handle Telegram-specific keyboards, callbacks, formatting, and menu behavior

## Remove from Telegram layer

- LangChain message parsing
- direct prompt or graph invocation logic
- tool output JSON parsing
- threadpool orchestration hacks caused by sync AI API design

## Future reuse

With this boundary in place:

- mobile app can call the same application services
- web app can call the same application services
- a future HTTP API can be added without rewriting core behavior

---

## Proposed File Structure

```text
app/
  interfaces/
    telegram/
      handlers/
      mapper.py
      presenter.py

  application/
    context.py
    contracts.py
    services/
      conversation_service.py
      task_service.py
      task_query_service.py

  ai/
    engine/
      flow.py
      nodes.py
      schemas.py
      llm.py
      resolver.py
      history.py
      tracing.py

  domain/
    services/
    exceptions.py

  infrastructure/
    persistence/
    llm/
    tracing/
    security/

  models/
    user.py
    task.py
    reminder.py
    conversation_turn.py
```

This structure is a target shape. Migration can be incremental.

---

## File-by-File Migration Map

## Delete

- `app/ai/graph/agent.py`
- `app/ai/graph/__init__.py`

## Refactor heavily

- `app/ai/tools/task_tools.py`
  - remove LangChain `@tool`
  - move logic into plain services

- `app/ai/prompts/system.py`
  - replace tool-agent prompt with planner / clarification / reply prompts

- `app/bot/handlers/conversation.py`
  - remove LangChain and LangGraph coupling
  - call application service only
  - return Telegram-rendered `ApplicationResult`

- `app/config.py`
  - remove LangSmith / LangChain settings
  - add LiteLLM / Langfuse / tracing config

- `pyproject.toml`
  - remove LangGraph / LangChain / LangSmith deps
  - add PocketFlow / LiteLLM / pocketflow-tracing / Langfuse deps

- `.env.example`
  - remove LangSmith variables
  - add LiteLLM / Langfuse / tracing variables if needed

- `README.md`
  - rewrite architecture and setup docs

## Keep mostly stable

- `app/models/user.py`
- `app/models/task.py`
- `app/models/reminder.py`
- settings/onboarding flows conceptually, but routed through cleaner services if needed

## Create

- `app/application/context.py`
- `app/application/contracts.py`
- `app/application/services/conversation_service.py`
- `app/application/services/task_service.py`
- `app/application/services/task_query_service.py`
- `app/ai/engine/flow.py`
- `app/ai/engine/nodes.py`
- `app/ai/engine/schemas.py`
- `app/ai/engine/llm.py`
- `app/ai/engine/resolver.py`
- `app/ai/engine/history.py`
- `app/ai/engine/tracing.py`
- `app/interfaces/telegram/mapper.py`
- `app/interfaces/telegram/presenter.py`
- `app/models/conversation_turn.py`
- `tests/` tree

---

## Migration Phases

## Phase 0 — Baseline and safety

### Goals

- capture supported current behavior
- create test safety net
- freeze migration decisions

### Tasks

- document supported intents and edge cases
- create golden conversation examples
- add unit/integration test skeleton
- identify sample real-world flows for regression checks

### Exit criteria

- baseline tests exist
- migration scope and architecture locked

---

## Phase 1 — Extract business logic from LangChain tools

### Goals

- remove framework coupling from business logic
- create plain async services

### Tasks

- refactor task/reminder operations out of LangChain tool decorators
- create service interfaces for task mutation and queries
- isolate timezone and validation logic

### Exit criteria

- domain operations can run without LangChain tools
- services are testable directly

---

## Phase 2 — Add application boundary

### Goals

- decouple Telegram from core behavior
- introduce channel-agnostic contracts

### Tasks

- add `RequestContext`
- add `ApplicationResult`
- add minimal interaction model
- create `ConversationService`
- make Telegram handler depend on application service, not AI graph internals

### Exit criteria

- Telegram handler no longer depends on LangChain types
- core returns application results

---

## Phase 3 — Build PocketFlow engine

### Goals

- replace LangGraph orchestration with PocketFlow
- standardize all model access through LiteLLM

### Tasks

- implement planner schema and structured output validation
- build PocketFlow nodes for load/plan/resolve/execute/render/persist
- implement LiteLLM adapter
- integrate domain services into workflow

### Exit criteria

- end-to-end conversation path works through PocketFlow
- no LangGraph runtime needed for message handling

---

## Phase 4 — History and clarification persistence

### Goals

- preserve short-term context across restarts
- support safe clarification flows

### Tasks

- add `ConversationTurn` persistence
- define session/history loading strategy
- persist clarification state where needed

### Exit criteria

- restart does not break short-term conversation continuity
- ambiguity always leads to explicit clarification

---

## Phase 5 — Observability

### Goals

- trace conversation flow and major nodes
- avoid leaking secrets

### Tasks

- integrate `pocketflow-tracing`
- connect Langfuse
- add trace IDs/session IDs to request context
- redact secrets and sensitive data in tracing/logging

### Exit criteria

- traces visible in Langfuse
- no sensitive values leak into traces

---

## Phase 6 — Cleanup and documentation

### Goals

- remove dead stack pieces
- leave clean codebase and clear docs

### Tasks

- remove LangGraph / LangChain / LangSmith imports and deps
- regenerate lockfile
- rewrite README/setup docs
- document new architecture and boundaries

### Exit criteria

- no Lang* runtime pieces remain
- docs match implementation

---

## Testing Strategy

## Unit tests

- task creation/edit/delete/done services
- reminder logic
- reference resolution behavior
- timezone conversion behavior
- planner schema validation
- application result mapping

## Flow tests

- PocketFlow branch selection
- ambiguity / clarification branch
- execution branch by intent
- error / retry behavior where relevant

## Integration tests

- Telegram adapter -> application service -> PocketFlow -> persistence
- mocked LiteLLM planner output
- conversation history load/save
- tracing integration smoke test if practical

## Golden transcript tests

- create task from natural language
- list tasks
- mark task done
- delete task
- edit task
- ambiguous reference must ask for clarification

---

## Acceptance Criteria

- no `langgraph`, `langchain`, or `langsmith` imports remain in application code
- all model calls go through one LiteLLM adapter
- PocketFlow orchestration handles conversation flow
- Telegram layer contains no AI framework internals
- core returns application results, not Telegram/LangChain types
- short-term history survives restarts
- ambiguous references always ask before mutating data
- tracing works with Langfuse
- decrypted API keys never enter traces or logs
- tests cover core CRUD/reminder/stats/clarification flows

---

## Risks and Mitigations

## Risk: task reference resolution quality

Mitigation:

- deterministic resolver logic
- explicit clarification flow
- transcript-based tests for ambiguity cases

## Risk: structured LLM output inconsistency

Mitigation:

- strict schema validation
- narrow intent set
- deterministic fallback behavior

## Risk: over-designing cross-channel abstractions too early

Mitigation:

- keep interaction model minimal now
- defer rich generic UI action taxonomy

## Risk: tracing leaks sensitive data

Mitigation:

- never include decrypted keys in shared state
- redact sensitive payloads before tracing/logging

## Risk: migration leaves mixed old/new architecture behind

Mitigation:

- delete Lang* stack completely after new workflow is verified
- rewrite README/config/docs in same migration effort

---

## What to Defer

Do not build these now unless a new real interface requires them:

- full HTTP/mobile transport DTO layer
- rich generic UI action framework
- full auth model
- RBAC/permissions
- account linking across channels
- multi-provider user-key design

Design only the seam now, not the full future system.

---

## Recommended Implementation Order Summary

1. add tests and baseline transcripts
2. extract business logic from LangChain tools into plain services
3. add application boundary (`RequestContext`, `ApplicationResult`, services)
4. refactor Telegram handler to use application service only
5. implement LiteLLM adapter
6. build PocketFlow workflow and nodes
7. add conversation history persistence
8. add tracing with Langfuse
9. remove Lang* dependencies and dead code
10. rewrite docs and clean project structure

---

## Bottom Line

This migration should not be a mechanical LangGraph-to-PocketFlow rewrite.

It should be a structural cleanup:

- PocketFlow becomes a small orchestration layer
- LiteLLM becomes the single LLM gateway
- application services become the true core boundary
- Telegram becomes a thin adapter
- domain logic becomes framework-agnostic
- short-term history becomes explicit and durable

If executed this way, the codebase becomes cleaner now and ready for future interfaces later.
