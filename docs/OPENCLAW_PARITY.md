# OpenClaw parity matrix (reference only)

Источник: [openclaw/openclaw](https://github.com/openclaw/openclaw), [docs.openclaw.ai](https://docs.openclaw.ai/).

**CLI OpenClaw в agentsTG не устанавливаем** — портируем паттерны на Python/aiogram.

## Delivery & streaming

| OpenClaw | Документация | agentsTG | Статус |
|----------|--------------|----------|--------|
| Block chunking | [streaming](https://docs.openclaw.ai/concepts/streaming) | `channels/telegram_delivery.py` | W1.1 |
| Preview streaming | Telegram editMessageText | optional phase 2 | planned |
| textChunkLimit 4096 | per channel | `split_telegram_html` | W1.1 |
| Coalesce blocks | idleMs merge | later | backlog |
| humanDelay | 800–2500ms between bubbles | later | backlog |
| Delivery retry | retry on fail | 2× retry | W1.1 |

## Message pipeline

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| inbound debounce 2s | `message_pipeline.py` | W1.3 |
| dedupe message_id | Redis/memory | W1.3 |
| queue steer/followup | per-chat queue | W1.3 |
| per-chat sequencing | per-chat lock | W1.3 |

## Time & autonomy

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| `cron add --at --tz` | `reminder_service` APScheduler | W1.7 |
| agent turn on wake | `AgentRun(trigger=cron)` | W1.2 |
| heartbeat / proactive | 09:00 MSK digest | W2.5 |

## Agent bootstrap

| OpenClaw file | agentsTG | Статус |
|---------------|----------|--------|
| SOUL.md | `agents/souls/*.md` | done |
| AGENTS.md | CursoRules + `agent_prompts.py` | done |
| IDENTITY.md | `agent_identity.py` | done |
| USER.md | `user_profiles` + bootstrap USER block | done |
| MEMORY.md | `workspace/.../MEMORY.md` + curated block | done |
| memory/YYYY-MM-DD.md | `workspace_memory.append_daily_log` | done |
| TOOLS.md | `agents/tools/{agent_key}.md` | done |
| Shared FOCUS | `user_projects` + `project_activity` | done |
| Cross-agent journal | `log_project_activity` + auto-log | done |

## Multi-agent

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| NO_REPLY silent | group orchestrator | W2.4 |
| deterministic routing | 7 separate bots | exists |
| delegation | orchestrator LangGraph | W2.3 improve |

## Groq vs wrapper

OpenClaw abstract provider; мы используем Groq free tier — 429 и TPM лимиты **дополняют**, но не заменяют дыры в delivery/runtime.
