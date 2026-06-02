# OpenClaw parity matrix (reference only)

Источник: [openclaw/openclaw](https://github.com/openclaw/openclaw), [docs.openclaw.ai](https://docs.openclaw.ai/).

**CLI OpenClaw в agentsTG не устанавливаем** — портируем паттерны на Python/aiogram.

Легенда: **done** | **partial** | **backlog** | **planned**

## Delivery & streaming

| OpenClaw | Документация | agentsTG | Статус |
|----------|--------------|----------|--------|
| Block chunking | [streaming](https://docs.openclaw.ai/concepts/streaming) | `telegram_delivery.py` | done |
| Preview streaming | Telegram editMessageText | `channels/delivery/streaming.py` + `OutboundSink` | done |
| textChunkLimit 4096 | per channel | `split_telegram_html` | done |
| Coalesce blocks | idleMs merge | `gateway/coalesce.py` + `OutboundSink` | done |
| humanDelay | 800–2500ms between bubbles | `HUMAN_DELAY_MS_*` in `telegram_delivery.py` | done |
| Delivery retry | retry on fail | 2× retry | done |

## Message pipeline

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| inbound debounce 2s | `message_pipeline.py` | done |
| dedupe message_id | gateway + `message_pipeline` | done |
| queue steer/followup | per-chat queue | done |
| per-chat sequencing | per-chat lock | done |

## L2 Gateway

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| OpenClawEnvelope | `gateway/envelope.py` | done |
| TelegramAdapter | `channels/telegram_adapter.py` | done |
| Session manager | `gateway/session.py` | done |
| Task Brain / agent_jobs | `gateway/job_store.py` + PG | done |
| Idempotency | gateway dispatch + job_store | done |
| HTTP agent/run | `health_server.py` POST `/v1/agent/run` | done |
| A2A callback | POST `/v1/webhook/a2a/callback` | done (stub) |
| WS / OpenAI-compat API | — | backlog |

## Security hooks

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| before_prompt_build | `hook_registry` + injection_guard | done |
| before_tool_call | `tool_policy` hook + `tool_policies.py` (tier + deny + validators) | done |
| after_tool_exec | JOURNAL.md audit (+ tier in payload) | done |

## Prompt layer (OpenClaw-style)

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| SOUL.md | `agents/souls/*.md` | done |
| system directives | `prompts/system_directives.py` | done |
| per-agent style | `prompts/styles/` | done |
| orchestrator routing JSON v2 | `orchestrator_directives.py` + `supervisor_parse.py` | done |
| finalize pass | `finalize_directives.py` (structured HTML) | done |
| proactive wake | `prompts/proactive.py` + `agent_wake.py` | done |
| replan directive | `REPLAN_DIRECTIVE` + orchestrator | done |

## Time & autonomy

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| cron / scheduler | `reminder_service` APScheduler + poll | partial |
| agent turn on wake | `AgentRun(trigger=cron)` | done |
| heartbeat | PA + orchestrator check-in | done |
| activeHours / skipWhenBusy | `agent_wake.py` + settings | done |
| event wake | `run_event_wake` | done |
| proactive policy | `proactive_policy.py` | done |

## Manus layer

| Manus | agentsTG | Статус |
|-------|----------|--------|
| Plan executor | `plan_executor.py` + LangGraph loop | done |
| Outer loop / max turns | `agent_outer_loop.py` | partial |
| Progress UX | step messages in delegate | partial |
| Artifacts sendDocument | `artifact_service.py` | partial |
| Confirmation TG buttons | `confirmation_service` + callbacks | done |
| AgentTask FSM PG | `agent_tasks` + `plan_steps` | done |

## Agent bootstrap

| OpenClaw file | agentsTG | Статус |
|---------------|----------|--------|
| SOUL.md | `agents/souls/*.md` | done |
| per-agent workspace | `workspace/users/{id}/agents/{role}/` | done |
| JOURNAL.md | `append_journal_md` + `/journal` | done |
| Confirmation gates | PG + `REQUIRE_CONFIRM` | partial |

## L4 Execution

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| Plugin registry | `plugins/registry.py` + plugin.yaml | partial |
| MCP bridge | `mcp/client.py` stub | partial |
| Sandbox run_code | `sandbox/docker_runner.py` | partial (subprocess, no Docker yet) |
| Browser tools | httpx fallback in `role_tools` | partial |

## Multi-agent

| OpenClaw | agentsTG | Статус |
|----------|----------|--------|
| 7 separate bots | unchanged | done |
| Gateway envelope layer | `agent_bot → gateway → dispatch` | done |
| delegation | PlanExecutor + orchestrator graph | partial |

## Ops

| Item | Статус |
|------|--------|
| Health + PG ping | `curl :8080/` → `database.status` |
| Neon PG + migrations | `f8a1c3d5e927` — run `alembic upgrade head` |
| E2E W1–W10 | см. [E2E_AUTONOMY.md](E2E_AUTONOMY.md) |
| Node sidecar migration | см. [OPENCLAW_SIDECAR_EVAL.md](OPENCLAW_SIDECAR_EVAL.md) |
