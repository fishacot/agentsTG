# Roadmap MVP: личный штаб в Telegram (6–12 месяцев)

Living document. Канон процесса: [`AGENTS.md`](../AGENTS.md), verify: [`PROJECT_VERIFICATION.md`](PROJECT_VERIFICATION.md).

**Аудитория MVP:** один владелец (solo). **Интеграции:** сбалансированно (якорь на 2–3 роли).

## Эталоны

| Эталон | Документ |
|--------|----------|
| Поведение 7 ботов | [`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md) |
| OpenClaw parity | [`OPENCLAW_PARITY.md`](OPENCLAW_PARITY.md) |
| Research (promt 1–4) | [`research/README.md`](research/README.md) |
| E2E приёмка | [`E2E_AUTONOMY.md`](E2E_AUTONOMY.md) |
| Deploy | [`deploy/FIRSTBYTE_VPS.md`](../deploy/FIRSTBYTE_VPS.md) |

**Не делаем:** свою LLM, desktop Manus, Firecracker в критическом пути, MCP hub на всех 7 ботов.

## Критерии «автономно как Manus/OpenClaw»

| Критерий | Измерение (solo) |
|----------|------------------|
| Многошаговость | E2E W6, W11 D1–D4 |
| Надёжность | verify + JOURNAL |
| Безопасность | D6 confirm, hooks |
| Память по задаче | D10 |
| Интеграции | calendar + github + research cite |
| Время | W2 напоминания, digest |

**MVP done (фаза 2):** 30 дней ежедневного использования + E2E W1–W11 подписаны + 3 интеграции.

## Фазы

### Фаза 0 — Prod-доверие (недели 1–4)

- VPS + Neon, `alembic upgrade head`
- E2E W1–W6 + W11 D1–D6 в implementation-notes
- Confirmation inline + replay `run_code`
- `/journal` audit

### Фаза 1 — Manus-loop (месяц 1–2)

- `editMessageText` + cancel keyboard
- `tool_results` → verify
- `task_id` в chat_history
- Delegation: reply_to + handoff copy
- business/marketing styles

### Фаза 2 — Интеграции MVP (месяц 2–4)

- Calendar (PA), GitHub (coder), research cite (Ульяна)
- [`INTEGRATIONS.md`](INTEGRATIONS.md)
- MCP POC (1 сервер)
- Егор: сводка `agent_tasks`

### Фаза 3 — Правила и интеллект (месяц 4–6)

- `workspace/.../RULES.md` playbook
- assembler v2 + recipe store
- [`METRICS.md`](METRICS.md)

### Фаза 4 — OpenClaw platform (месяц 6–9)

- HTTP API + `AGENT_RUN_API_TOKEN`
- Delegation v2 callbacks
- Model routing per step

### Фаза 5 — Зрелость (месяц 9–12)

- [`EVAL_HARNESS.md`](EVAL_HARNESS.md)
- [`WEB_APPS.md`](WEB_APPS.md) (опционально)
- [`FIRECRACKER_SPIKE.md`](FIRECRACKER_SPIKE.md) go/no-go

## Потоки работ

| Поток | Фокус |
|-------|--------|
| A Trust & Ops | deploy, E2E, Neon |
| B Manus UX | plan, verify, confirm |
| C Prompts & rules | SOUL, playbook, recipes |
| D Integrations | calendar, github, MCP |
| E Platform | gateway, HTTP, A2A |
| F Quality | metrics, eval |

## Риски (текущий VPS + Groq)

| Риск | Митигация |
|------|-----------|
| RAM ~1 GB | без Ollama; Neon + файловый workspace |
| Groq 429 / TPM | cooldown, `LLM_SOFT_DAILY_CALLS`, LIGHT tier при 85% бюджета |
| Длинные планы | `MAX_PLAN_STEPS=4` |
| Потеря контекста | NOTEBOOK.md + PG facts + `append_notebook` |

Подробно: [`RESOURCE_AND_LLM.md`](RESOURCE_AND_LLM.md).

## MVP Done checklist

- [ ] E2E W1–W11 (D1–D6 минимум) — дата в implementation-notes
- [ ] Calendar integration smoke
- [ ] GitHub integration smoke
- [ ] Research cite smoke
- [ ] 30 дней solo journal (weekly bullets)

См. также wave 2–5 в [`research/README.md`](research/README.md).
