# OpenClaw parity matrix (reference only)

Источник: [openclaw/openclaw](https://github.com/openclaw/openclaw), [docs.openclaw.ai](https://docs.openclaw.ai/).

**CLI OpenClaw в agentsTG не устанавливаем** — портируем паттерны на Python/aiogram.

Легенда: **done** | **partial** | **backlog** | **planned**

## Delivery & streaming

| OpenClaw | Документация | agentsTG | Статус |
|----------|--------------|----------|--------|
| Block chunking | [streaming](https://docs.openclaw.ai/concepts/streaming) | `telegram_delivery.py` | done |
| Preview streaming | Telegram editMessageText | — | planned |
| textChunkLimit 4096 | per channel | `split_telegram_html` | done |
| Coalesce blocks | idleMs merge | — | backlog |
| humanDelay | 800–2500ms between bubbles | — | backlog |
| Delivery retry | retry on fail | 2× retry | done |

## Message pipeline

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| inbound debounce 2s | `message_pipeline.py` | done |
| dedupe message_id | memory | done |
| queue steer/followup | per-chat queue | done |
| per-chat sequencing | per-chat lock | done |

## Time & autonomy

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| `cron add --at --tz` | `reminder_service` poll + PG | partial (poll, not APScheduler) |
| agent turn on wake | `AgentRun(trigger=cron)` via `run_scheduled_reminder` | done |
| heartbeat / proactive | PA heartbeat + orchestrator check-in + digest 09:00 | done |
| event wake after background | `run_event_wake` | done |
| proactive policy per agent | `proactive_policy.py` | done |

## Agent bootstrap

| OpenClaw file | agentsTG | Статус |
|---------------|----------|--------|
| SOUL.md | `agents/souls/*.md` | done |
| AGENTS.md | CursoRules + `agent_prompts.py` | done |
| IDENTITY.md | `agent_identity.py` | done |
| USER.md | `user_profiles` + bootstrap USER block | done |
| MEMORY.md | `workspace/.../MEMORY.md` + `refresh_memory_md` | partial (sync on fact/project) |
| memory/YYYY-MM-DD.md | `workspace_memory.append_daily_log` | done |
| JOURNAL.md | `append_journal_md` (Manus log) | done |
| TOOLS.md | `agents/tools/{agent_key}.md` | done |
| Shared FOCUS | `user_projects` + `project_activity` | done |
| Cross-agent journal | auto-log + JOURNAL.md | done |
| Confirmation gates | `confirmation_service` + `REQUIRE_CONFIRM` | partial (MVP) |

## Multi-agent

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| NO_REPLY silent | group orchestrator | done |
| deterministic routing | 7 separate bots | done |
| delegation | orchestrator LangGraph + async delegate | partial |
| Gateway envelope layer | direct `agent_bot → runtime` | backlog |

## Groq vs wrapper

OpenClaw abstract provider; мы используем Groq/Gemini chain — 429 и TPM лимиты **дополняют**, но не заменяют дыры в delivery/runtime.

## Ops

| Item | Статус |
|------|--------|
| Neon PG persistence on VPS | partial — требует `DATABASE_URL` + `alembic upgrade head` |
| E2E W1–W3 | см. [E2E_AUTONOMY.md](E2E_AUTONOMY.md) |
