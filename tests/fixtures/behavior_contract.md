# Phase 0 behavior contract

Supported today:

- create task
- create reminder
- list tasks
- mark task done
- delete task
- edit task
- get task stats
- reminders
- conversation reply passthrough from agent/tool output

Known edge cases covered by tests:

- missing Telegram user data
- missing registered user
- missing OpenAI API key
- invalid tool JSON fallback
- direct AI response passthrough
- generic conversation exception
- markdown parse fallback
