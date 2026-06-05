---
summary: План prod LLM-цепочки, env-матрицы, OpenClaw parity и апгрейда E2E (фазы A–C)
read_when: настройка VPS/.env, sign-off E2E, сопоставление с OpenClaw, roadmap LLM
---

# План: топовая LLM-цепочка + настройки репо + OpenClaw + E2E

> Синтез из кода (`settings.py`, `llm_client.py`, `agent_models.py`), деплоя (`deploy/FIRSTBYTE_VPS.md`), OpenClaw parity и E2E-матрицы W1–W11.

## Executive summary

- **Prod LLM на VPS:** `LLM_PROVIDER_CHAIN=groq` — Gemini с датацентра блокируется; в коде дефолт `gemini,groq` → HF как tertiary.
- **Fallback и guardrails:** цепочка провайдеров + cooldown 3–4s + soft budget 80 вызовов/день + defer heavy @ 85%.
- **OpenClaw:** envelope/gateway/heartbeat/Manus-loop в основном **done**; gaps — A2A/WS, MCP hub, delegation v2, Node sidecar отложен.
- **E2E:** pytest green, **W1–W11 sign-off в prod pending**; фаза 0 = human sign-off + `REQUIRE_CONFIRM=true` + replay D6/`run_code`.
- **Не на VPS:** AirLLM, Ollama на ~1GB RAM — см. `docs/DEV_AGENT_ERGONOMICS.md`, `deploy/OLLAMA_VPS.md`.

---

## Текущее состояние

| Область | Сейчас (код/доки) | Prod VPS (канон) | Gap |
|--------|-------------------|------------------|-----|
| Provider chain | Default `gemini,groq` | `groq` only | Gemini на VPS недоступен |
| Модели | Matrix в `agent_models.py`; coder → `qwen/qwen3-32b` (Groq) | То же | `MODEL_*` overrides редко |
| Budget/cooldown | 80 calls/day, 3–4s cooldown | 80, 4.0s | Redis опционален |
| OpenClaw parity | ~90% delivery/gateway/Manus **done** | То же runtime | A2A, WS, MCP hub **partial** |
| E2E | pytest green; матрица W1–W11 | Sign-off **pending** | Human + Telegram |

---

## Целевое состояние

| Столбец | Target |
|---------|--------|
| **Top chain** | VPS: `groq` (+ ключ); dev/staging: `gemini,groq` при рабочем Gemini; HF только как tertiary |
| **OpenClaw parity** | Закрыть P0 E2E; P2 CalDAV write + MCP POC; delegation v2 + documented HTTP API |
| **E2E maturity** | `E2E_SIGNOFF_TEMPLATE.md` заполнен; W1–W11 D1–D6; 30 дней journal; eval 20+ fixtures из W11 |

---

## Top LLM chain

### Порядок провайдеров

`settings.LLM_PROVIDER_CHAIN` → `llm_provider_chain_list()` → `llm_client._chain()` — только провайдеры с ключом. Auto-fallback: groq → gemini → huggingface (`QWEN_API_KEY`).

| Среда | `LLM_PROVIDER_CHAIN` | Причина |
|-------|----------------------|---------|
| VPS FirstByte | `groq` | `.env.example`: Gemini blocks datacenter IPs |
| Local dev | `gemini,groq` или `groq` | Больше квот / тест Gemini |
| Tertiary | `...,huggingface` | Только с `QWEN_API_KEY` |

### Модели по агенту (Groq, без `MODEL_*`)

| agent_key | Модель |
|-----------|--------|
| orchestrator, PA, research, security, business, marketing | `llama-3.1-8b-instant` |
| coder | `qwen/qwen3-32b` |
| general | `llama-3.1-8b-instant` |

### Gemini matrix (когда доступен)

| agent_key | Модель |
|-----------|--------|
| orchestrator, security, business | `gemini-2.5-flash-lite` |
| PA, coder, research, marketing | `gemini-2.5-flash` |

### Fallbacks в runtime

- `RateLimitError` / retryable `QwenAPIError` → следующий провайдер в цепочке.
- Исчерпан `LLM_SOFT_DAILY_CALLS` → `RateLimitError` до смены дня.
- Retry 429/503: до 6 попыток с backoff.

### Rate limits (guardrails, не API quota)

| Механизм | Env | Default |
|----------|-----|---------|
| Inter-call cooldown | `LLM_COOLDOWN_SEC` | 3.0 (VPS 4.0) |
| Daily soft cap | `LLM_SOFT_DAILY_CALLS` | 80 (0=off) |
| Heavy defer | `GROQ_DEFER_HEAVY_ON_BUDGET` | true @ 85% |
| Plan length | `MAX_PLAN_STEPS` | 4 |
| Full tier tokens | `MAX_TOKENS_FULL_TIER` | 900 (VPS doc 768) |
| Concurrency | code | global sem=1, per-agent=2 |

---

## Матрица настроек: repo vs VPS vs local

| Variable | VPS | Local dev | Notes |
|----------|-----|-----------|-------|
| `LLM_PROVIDER_CHAIN` | `groq` | `gemini,groq` | Comma-separated |
| `GROQ_API_KEY` | required | required | |
| `GEMINI_API_KEY` | skip on VPS | optional primary | DC block |
| `QWEN_API_KEY` | optional | optional | Enables `huggingface` in chain |
| `GROQ_MODEL` / `GEMINI_MODEL` | defaults OK | defaults OK | Override rare |
| `MODEL_ORCHESTRATOR` … `MODEL_MARKETING` | empty unless tuning | optional | Beats provider matrix |
| `MODEL_DEFAULT` | optional | optional | `general` |
| `LLM_COOLDOWN_SEC` | `4.0` | `3.0`+ | |
| `LLM_SOFT_DAILY_CALLS` | `80` | `80` | `0` disables |
| `GROQ_DEFER_HEAVY_ON_BUDGET` | `true` | `true` | |
| `MAX_PLAN_STEPS` | `4` | `4` | |
| `MAX_TOKENS_FULL_TIER` | `768` recommended | `900` code default | |
| `STEP_MODEL_ROUTING` | JSON optional | JSON optional | `plan_step`, `agent`, `finalize` |
| `VERIFY_LLM_JUDGE` | `false` | `false` | expensive |
| `MCP_ENABLED` | `false` | `false` POC | orchestrator only |
| `HEARTBEAT_*` | see `.env.example` | tune quiet hours | OpenClaw parity |
| `REQUIRE_CONFIRM` | **target `true`** | `false` dev | E2E D6 |
| `AGENT_RUN_API_TOKEN` | set for HTTP | optional | phase 4 |
| `REDIS_URL` | recommended | optional | cooldown + budget |
| `DATABASE_URL` | Neon | local/PG | reminders, plans |

Полный список: `.env.example`, `src/agents_tg/config/settings.py`, `deploy/FIRSTBYTE_VPS.md`.

---

## OpenClaw alignment

| Концепт OpenClaw | agentsTG | Статус |
|------------------|----------|--------|
| Envelope + adapter | `gateway/envelope.py`, telegram adapter | done |
| Debounce/dedupe/queue | `message_pipeline.py` | done |
| Heartbeat / activeHours | `agent_wake.py`, `HEARTBEAT_*` | done |
| SOUL + styles + bootstrap | `agents/souls`, `prompts/` | done |
| Tool hooks | `hook_registry`, `tool_policies` | done |
| Plan executor / confirm replay | `plan_executor`, confirmation replay | done (E2E pending) |
| HTTP agent/run | `health_server.py` | done (token) |
| A2A callback | webhook partial | partial |
| MCP / plugins | `MCP_ENABLED`, plugins registry | partial MVP |
| WS / OpenAI-compat | — | backlog |
| Node sidecar | — | deferred (`OPENCLAW_SIDECAR_EVAL.md`) |

Детали: `docs/OPENCLAW_PARITY.md`, интеграции — `docs/INTEGRATIONS.md`, runtime — `docs/AGENT_RUNTIME.md`.

---

## Phased roadmap

### Phase A — Trust & LLM ops (2–4 недели)

| # | Задача | Owner | Verify |
|---|--------|-------|--------|
| A1 | VPS `.env`: `LLM_PROVIDER_CHAIN=groq`, budget block | human/ops | `curl :8080/`, journalctl без 429 storm |
| A2 | E2E W1–W3, W5#19–20, W6, W11 D1–D6 | human | `E2E_SIGNOFF_TEMPLATE.md` |
| A3 | `REQUIRE_CONFIRM=true` на VPS; D6 replay | human | W11 D6–D8 |
| A4 | Neon + `alembic upgrade head` | agent/ops | W1#4, W3#14 |
| A5 | Синхрон docs default chain vs VPS | agent | `npm run verify` |

### Phase B — Manus + integrations + eval (1–3 мес.)

| # | Задача | Owner | Verify |
|---|--------|-------|--------|
| B1 | `STEP_MODEL_ROUTING` в prod | agent | pytest + manual smoke |
| B2 | CalDAV write или явный defer | agent | `INTEGRATIONS.md` smoke |
| B3 | Map W11 D1–D10 → `test_eval_scenarios.py` | agent | `pytest tests/test_eval_scenarios.py -v` |
| B4 | GitHub + research cite prod smoke | human | `ROADMAP_MVP` checklist |

### Phase C — OpenClaw platform (3–6+ мес.)

| # | Задача | Owner | Verify |
|---|--------|-------|--------|
| C1 | `AGENT_RUN_API_TOKEN` + HTTP runbook | ops | POST `/v1/agent/run` |
| C2 | MCP POC 1 stdio server | agent | `MCP_ENABLED=true` orchestrator only |
| C3 | Delegation v2 / A2A resume hardening | agent | E2E D3 + unit tests |
| C4 | Re-read `OPENCLAW_SIDECAR_EVAL.md` (Node defer) | human | decision log in notes |

**Verify канон (все фазы):** `python -m pytest tests/ -v --tb=short`; перед PR — black, flake8, mypy; после `.md` — `npm run verify`. См. `docs/PROJECT_VERIFICATION.md`.

---

## Риски и что НЕ делать

| Не делать | Почему | Источник |
|-----------|--------|----------|
| AirLLM на VPS | CPU, API mismatch, latency | `docs/DEV_AGENT_ERGONOMICS.md` |
| Ollama на ~1GB VPS | RAM | `deploy/FIRSTBYTE_VPS.md` |
| `LLM_PROVIDER_CHAIN=gemini,...` на VPS без проверки IP | Блокировка DC | `.env.example` |
| `MODEL_ORCHESTRATOR=70b` на free Groq | TPM 429 | `agent_models.py` |
| Firecracker/MCP hub на всех 7 ботов в критическом пути | Scope | `docs/ROADMAP_MVP.md` |
| Считать MVP done без E2E sign-off + 30 дней | Trust gap | `MVP_GAP_AUDIT.md` |

---

## Связанные документы

| Документ | Назначение |
|----------|------------|
| `docs/ROADMAP_MVP.md` | Фазы 0–5, общий roadmap |
| `docs/E2E_AUTONOMY.md` | E2E матрица, W11 |
| `docs/OPENCLAW_PARITY.md` | Детальная parity-таблица |
| `deploy/FIRSTBYTE_VPS.md` | VPS env и deploy |
| `.env.example` | Шаблон переменных |

---

## Источники в коде

- `src/agents_tg/config/settings.py`
- `src/agents_tg/services/llm_client.py`
- `src/agents_tg/services/agent_models.py`
- `src/agents_tg/services/llm_budget.py`
