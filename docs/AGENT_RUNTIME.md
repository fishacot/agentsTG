# Agent Runtime — chatbot vs agent

## Текущее состояние (agent runtime, 2026-06)

```
Trigger (inbound | cron | background | delegation)
  → AgentRuntime.run_inbound / run_scheduled
  → agent_runner (LLM + tools, tier profiles)
  → OutboundSink: 0..N Telegram messages
  → ReminderService / AgentWakeService (фон VPS)
```

**Реализовано:**

- `AgentRuntime` — inbound + scheduled (`TriggerKind`: CRON, BACKGROUND, DELEGATION)
- `ReminderService` — poll 30s, once/daily, утренний digest 09:00 МСK
- **Cron → AgentRun:** user reminders через `run_scheduled_reminder` (LLM + static fallback)
- `AgentWakeService` — heartbeat (PA), project check-in (Егор), LLM digest
- `proactive_intent` — materialize «каждый день в 11» до LLM
- `proactive_policy` — heartbeat только у PA; check-in у orchestrator
- `run_event_wake` — background research + async delegation
- Chat history в PG; Neon persistence (если `DATABASE_URL` на VPS)
- **Gateway L1–L3:** envelope → `dispatch_agent` → outer loop (см. [AGENT_PIPELINE.md](AGENT_PIPELINE.md))
- **Delivery:** preview streaming, coalesce, humanDelay, chunking (`OutboundSink`)

**Env:** `REMINDER_LLM_DELIVERY`, `HEARTBEAT_*`, `REQUIRE_CONFIRM`, `PREVIEW_STREAMING_ENABLED`, `COALESCE_IDLE_MS`.

## Backlog (не блокирует prod)

- Calendar tool, weekly cron recurrence E2E
- WS / OpenAI-compat API (см. [OPENCLAW_SIDECAR_EVAL.md](OPENCLAW_SIDECAR_EVAL.md))
- Docker sandbox, real browser, MCP beyond stub

## Триггеры

| Trigger | Пример | Агент |
|---------|--------|-------|
| `inbound` | Сообщение в ЛС | Все 7 |
| `cron` | «Напомни в 11:00 МСK» | Эльза |
| `background` | Долгий deep_research | Ульяна |
| `delegation` | Егор → specialist | Егор + specialist |

## Autonomy levels (7 ботов)

| agent_key | max_steps | multi-msg | time | background |
|-----------|-----------|-----------|------|------------|
| orchestrator | 2 | 1–2 | check-in | delegate |
| personal_assistant | 5 | yes | **yes** | reminders |
| coder | 4 | yes | no | optional |
| research | 5 | yes | no | **yes** |
| security_ai | 3 | yes | no | no |
| business_manager | 3 | yes | no | no |
| marketing | 3 | yes | no | no |

## Часовой пояс

Все пользовательские времена — **`APP_TIMEZONE=Europe/Moscow` (МСK)**.
Хранение в БД — UTC (`timestamptz`).

## Связанные документы

- [OPENCLAW_PARITY.md](OPENCLAW_PARITY.md) — матрица done/partial/backlog
- [E2E_AUTONOMY.md](E2E_AUTONOMY.md) — приёмка W1–W30
- [AGENT_PIPELINE.md](AGENT_PIPELINE.md) — inbound flow + file map
- [PROJECT_VERIFICATION.md](PROJECT_VERIFICATION.md) — verify
