# Agent Runtime — chatbot vs agent

## Текущее состояние (chatbot)

```
Telegram message → AgentBot.handle_message → agent_runner.run → str
  → send_agent_response (1× edit_text) → idle
```

- Нет фоновых процессов, cron, heartbeat.
- `MAX_TOOL_ROUNDS=1` — один проход инструментов.
- Напоминания и «утренний дайджест» описаны в soul, но **не выполняются runtime**.

## Целевое состояние (agent)

```
Trigger (inbound | cron | delegation)
  → AgentRun(session_id, agent_key)
  → loop: LLM + tools
  → OutboundSink: 0..N Telegram messages
  → optional: schedule / background task
```

## Триггеры

| Trigger | Пример | Агент |
|---------|--------|-------|
| `inbound` | Сообщение в ЛС | Все 7 |
| `cron` | «Напомни в 11:00 МСК» | Эльза |
| `background` | Долгий deep_research | Ульяна |
| `delegation` | Егор → specialist | Егор + specialist |

## Autonomy levels (7 ботов)

| agent_key | max_steps | multi-msg | time | background |
|-----------|-----------|-----------|------|------------|
| orchestrator | 2 | 1–2 | no | delegate |
| personal_assistant | 5 | yes | **yes** | reminders |
| coder | 4 | yes | no | optional |
| research | 5 | yes | no | **yes** |
| security_ai | 3 | yes | no | no |
| business_manager | 3 | yes | no | no |
| marketing | 3 | yes | no | no |

## Часовой пояс

Все пользовательские времена — **`APP_TIMEZONE=Europe/Moscow` (МСК)**.
Хранение в БД — UTC (`timestamptz`).

## Связанные документы

- [OPENCLAW_PARITY.md](OPENCLAW_PARITY.md) — откуда берём паттерны
- [PROJECT_VERIFICATION.md](PROJECT_VERIFICATION.md) — verify
- Master plan: `.cursor/plans/ruslan_+_elza_fixes_073e68b9.plan.md`
