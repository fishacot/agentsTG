# MVP gap audit — честная сверка с OpenClaw / Manus

**Дата:** 2026-05-31  
**Контекст:** roadmap фазы 0–5 отмечены «готово» в коде и unit-тестах; это **не** эквивалент месяцев работы OpenClaw/Manus без prod E2E и 30 дней эксплуатации.

## Вердикт

| Уровень | Смысл |
|---------|--------|
| **Код + pytest** | Большой объём Manus-loop, gateway, integrations-stub, recipes — **есть** |
| **Prod / Telegram E2E** | W1–W11, Neon на VPS, `REQUIRE_CONFIRM=true` — **не подписано** |
| **Паритет OpenClaw** | HTTP dispatch, A2A callback, envelope — **частично**; полный hub/MCP/WS — **нет** |
| **Паритет Manus** | План, verify, cancel, handoff, editMessage прогресс — **в коде**; E2E не подписан |

## P0 — доверие и обманчивые «done»

| # | Пробел | Было | Статус |
|---|--------|------|--------|
| P0-1 | E2E W1–W11 + D6 confirm | Шаблон `E2E_SIGNOFF_TEMPLATE.md` пустой | **Человек** + VPS |
| P0-2 | `REQUIRE_CONFIRM` | default `false` | Включить в prod `.env` для D6 |
| P0-3 | Neon + `alembic upgrade head` на VPS | Доки есть | **Ops**, не чат |
| P0-4 | Доки vs код | `OPENCLAW_PARITY` отставал | Синхронизировать после правок |
| P0-5 | `STEP_MODEL_ROUTING` не в runtime | Модуль без вызовов | **Исправлено:** `llm_client` + step_kind в plan/agent/finalize |
| P0-6 | `task_id` в плановых шагах | `chat_history` умел, dispatch — нет | **Исправлено:** `dispatch_agent` + `build_environment` |
| P0-7 | Confirm в фоновом плане | `OutboundSink` null в `background_runs` | **Исправлено:** sink в `orchestrator_delegate._work` + flush в `finally` |
| P0-8 | HTTP API без токена | `_check_api_token` → True | **Исправлено:** fail closed; только `DEBUG=true` без токена |

## P1 — Manus UX и делегирование

| # | Пробел | Действие |
|---|--------|----------|
| P1-1 | Прогресс плана — новые сообщения | **Исправлено:** `plan_progress.py` + edit в delegate |
| P1-2 | A2A только patch context | **Исправлено:** `on_a2a_step_callback` + resume handle |
| P1-3 | `chat_history_pg` без `task_id` | **Исправлено:** migration `g1h3i5j7k019` |
| P1-4 | Eval | 25 unit-сценариев ≠ 20–30 live Telegram регрессий |

## P2 — Интеграции и платформа

| # | Пробел | Действие |
|---|--------|----------|
| P2-1 | Calendar | Stub даже при `CALDAV_URL` — реальный CalDAV write |
| P2-2 | MCP | `mcp/client.py` echo/stub, не stdio hub |
| P2-3 | HTTP API | POST `/v1/agent/run` dispatch; нет OpenAI-compat / WS |
| P2-4 | Chroma/RAG | Post-MVP в `ROADMAP.md` | — |
| P2-5 | Firecracker / Web Apps | Spike-доки only | go/no-go по `FIRECRACKER_SPIKE.md` |

## Что реально сделано (не отменять)

- Gateway envelope, `agent_dispatch`, plan FSM PG, verify-lite + `tool_results`
- Confirmation PG + inline replay (`confirmation_delivery`, `role_tools` + `REQUIRE_CONFIRM`)
- GitHub API при `GITHUB_TOKEN`, research citations, notebook/Groq budget
- Playbook, plan recipes, `staff_summary`, HTTP token на agent run

## STEP_MODEL_ROUTING (после P0-5)

JSON в `.env`, ключи step_kind:

- `plan_step` — шаг плана
- `agent` — tool-loop
- `finalize` / `continue` — финализация ответа
- `{agent_key}:{kind}` — составной ключ

Пример: `{"finalize":"gemini-2.5-flash","plan_step":"llama-3.1-8b-instant"}`

## Промпты для wave 2–5 (если нужен внешний ресёрч)

Уже в репо: `docs/research/01-strategy.md` … `04-telegram-ux.md`.

| Wave | Промпт (кратко) |
|------|-----------------|
| 5 | Метрики solo-штаба: какие 5–7 KPI в `METRICS.md`, пороги алертов, без PII |
| 6 | Cost routing: таблица step_kind → модель при лимите Groq 100k TPM |
| 7 | CalDAV MVP: библиотека Python, минимальный create-event, ошибки auth |
| 8 | MCP production: один stdio-сервер (filesystem), allowlist, timeout |

## Приёмка MVP (из `ROADMAP_MVP.md`)

Не считать MVP закрытым, пока нет **всех трёх**:

1. 30 дней ежедневного использования (журнал)
2. E2E W1–W11 подписаны с датами
3. Три интеграции **в бою** (календарь сейчас stub — не засчитывать без CalDAV)

## Следующие шаги (рекомендуемый порядок)

1. Заполнить `E2E_SIGNOFF_TEMPLATE.md` — см. [`VPS_E2E_RUNBOOK.md`](VPS_E2E_RUNBOOK.md)
2. P2-1 CalDAV или явный defer в `INTEGRATIONS.md`
3. Live eval harness по `EVAL_HARNESS.md`
