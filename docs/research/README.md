# Research outputs (deep prompts → agentsTG)

Исходные файлы в корне репо (`ответ на промт*.md`) — копии здесь для версионирования.

| Файл | Исходный промпт | Тема |
|------|-----------------|------|
| [01-strategy.md](01-strategy.md) | Промпт 1 | Manus/OpenClaw gap, roadmap, «не делать» |
| [02-prompt-layer.md](02-prompt-layer.md) | `ответ на промт.md` | SOUL/styles, OpenClaw/Manus layering |
| [02-prompt-architecture.md](02-prompt-architecture.md) | `ответ на промт3.md` | Анти-паттерны, слоистая архитектура 2025–26 |
| [03-execution.md](03-execution.md) | `ответ на промт2.md` | Verify, sandbox, browser, confirmation, MCP |
| [04-telegram-ux.md](04-telegram-ux.md) | Промпт 4 | 7 ботов, delegation JSON, E2E, anti-spam |

## Reconciliation (research claim → код → статус)

| Claim | Код | Статус (2026-06) |
|-------|-----|------------------|
| Task Brain отсутствует | `plan_executor.py`, PG `agent_tasks` / `plan_steps` | **done** — усилить связку с delegation UX |
| Sandbox отсутствует | `sandbox/docker_runner.py` SANDBOX_MODE | **done** — Firecracker = P2 spike |
| Единый MANUS_SPECIALIST_STYLE | `prompts/styles/research.py`, `security.py`, `coder.py` | **done** (wave 1) |
| research → sports_analyst.md | `souls/research.md` + `identity.py` alias | **done** |
| Verify только эвристики | `verify_step.py` + `tool_schemas.py` | **done** |
| Confirmation partial | `confirmation_service` + `confirmation_replay.py` + callbacks + `OutboundSink` | **done** (replay + inline via `inbound_turn`) |
| Delegation только group | `orchestrator_delegate` + DM в `inbound_turn` | **done** (wave 1) |
| session_id в памяти | `memory_block.build_memory_block` | **done** (опциональный task_id) |
| MCP для 7 ботов | `mcp/client.py` MVP | **deferred** — POC Q2 |
| Firecracker | — | **deferred** — spike only |

## Стратегический backlog (после wave 1)

| P | Инициатива | Когда |
|---|------------|--------|
| P1 | 1 ниша + 1–2 внешних API | Месяц 2–3 |
| P1 | Tier + model routing per step | Постоянно |
| P2 | Recipe store успешных планов | Q2 |
| P2 | Telegram Web Apps | По запросу |
| — | Firecracker sandbox | Spike |
| — | MCP hub POC | Q2 |

См. [legacy-souls.md](legacy-souls.md) — SOUL не в runtime.

## Roadmap waves (implementation)

| Wave | Горизонт | Фокус | Канон |
|------|----------|-------|-------|
| **1** | done | research docs, prompt-layer, verify, delegation envelope, plan_cancel | implementation-notes 2026-06 |
| **2** | месяц 0–1 | Prod trust: E2E W11, confirm inline, run_code replay | [ROADMAP_MVP.md](../ROADMAP_MVP.md) фаза 0 |
| **3** | месяц 1–2 | Manus UX: progress/cancel, task_id history, handoff | фаза 1 |
| **4** | месяц 2–4 | **MVP:** calendar, GitHub, research cite, INTEGRATIONS.md | фаза 2 |
| **5** | месяц 4–12 | Playbook, recipes, metrics, HTTP/MCP, eval | фазы 3–5 |

Полный план: **[`docs/ROADMAP_MVP.md`](../ROADMAP_MVP.md)**.
