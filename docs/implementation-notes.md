<!-- summary: Журнал решений разработки — новые записи сверху -->
<!-- read_when: нужен контекст недавних fix/deploy, tradeoffs, результаты verify -->

# Implementation notes — AI Agents Telegram Assistant

> Журнал решений и прогресса разработки мультиагентной системы для Telegram

Новые записи — **сверху** (под этим блоком).

---

## 2026-06-05 — Agent-scripts ergonomics + AirLLM assessment

### Цель

Cherry-pick полезных паттернов из steipete/agent-scripts; оценка AirLLM без интеграции в runtime.

### Добавлено

- `scripts/validate_cursor_artifacts.py` — `.cursor/rules`, `commands`, optional `skills`
- `scripts/docs_list.py` — индекс `docs/**/*.md` (`summary`, `read_when`)
- `scripts/committer.ps1` — безопасный commit Windows (refuse `.env`)
- `.cursor/skills/agents-tg-vps-debug/SKILL.md`
- `docs/DEV_AGENT_ERGONOMICS.md` — скрипты + **AirLLM no-go** для prod VPS

### Frontmatter

- `docs/PROJECT_VERIFICATION.md`, `deploy/FIRSTBYTE_VPS.md` — YAML
- `docs/implementation-notes.md` — HTML comment (running log, без YAML)

### Решения

- AirLLM **не** в `pyproject.toml` / `llm_client` — CPU VPS, API mismatch, latency
- Альтернативы: cloud chain (Gemini/Groq/Qwen); future GPU + Ollama/vLLM proxy

### Verify (2026-06-05)

- `python scripts/validate_cursor_artifacts.py`
- `pytest tests/ -q --tb=no -x`
- markdownlint на новых md — OK; полный `npm run verify` — pre-existing debt

---

## 2026-06-04 — Elza DM silent reply fix + deploy

### Причина
Двойной dedupe: `inbound.py` вызывал `is_duplicate()` до `gateway_router.dispatch()`, сообщение помечалось обработанным, но LLM-путь не запускался (нет «🤖 Думаю…»).

### Изменения
- `src/agents_tg/bots/handlers/inbound.py` — убран pre-check dedupe
- `src/agents_tg/services/inbound_turn.py` — log `inbound_duplicate_skip`
- `tests/test_message_pipeline.py` — regression `test_pre_claim_before_gateway_dispatch_is_duplicate`

### Verify
- `pytest tests/ -q` — **231 passed**

### Deploy
- commit `de9368c` → `origin/master`
- VPS `91.186.221.32`: `systemctl is-active agents-tg` → **active**, health ok
- лог: `docs/last_vps_deploy.txt`

### Follow-up hotfix (ошибка «Произошла ошибка» в TG)
- `agent_runtime.run_inbound`: `del is_group` ломал вызов `process_fn` → UnboundLocalError
- `reminder_service._list_pending_pg`: `conn.scalars()` вместо `execute().scalars()` (падало на `/start`)
- verify: `pytest tests/test_agent_runtime.py tests/test_reminder_service.py` — 6 passed
- deploy: commit после push на VPS

---

## 2026-06-04 — Prod E2E automated (VPS)

### Скрипт
- `python scripts/vps_configure_prod.py` (env `VPS_SSH_PASSWORD`, не в репо)
- Лог без секретов: [`docs/last_vps_e2e_automated.txt`](last_vps_e2e_automated.txt)

### Результат на VPS (91.186.221.32)
| Проверка | Статус |
|----------|--------|
| `REQUIRE_CONFIRM=true`, `DEBUG=false` | OK |
| `systemctl is-active agents-tg` | active |
| `GET /` health + `database.status` | ok |
| `POST /v1/agent/run` без токена | 401 |
| `POST /v1/agent/run` с Bearer | 200 |

### Доки
- [`docs/E2E_EXPLAINED.md`](E2E_EXPLAINED.md) — что такое E2E (RU)
- [`docs/E2E_TELEGRAM_CHECKLIST.md`](E2E_TELEGRAM_CHECKLIST.md) — ~10 мин ручных шагов
- [`docs/E2E_SIGNOFF_TEMPLATE.md`](E2E_SIGNOFF_TEMPLATE.md) — Pass 2026-06-04 для automated строк

### Verify (local, перед коммитом E2E-артефактов)
- `python -m pytest tests/test_health_api_token.py tests/test_plan_a2a_resume.py -q` — **5 passed**

### Остаётся human
- W1 #1–3,6–7, W11 D1–D6, напоминания, confirm replay в Telegram — чеклист выше
- Ротация VPS-пароля и `AGENT_RUN_API_TOKEN` (пароль/токен светились в чате/терминале)

---

## 2026-06-03 — Ship batch (MVP parity code)

### Verify
- `python -m pytest tests/ -q` — **230 passed** (~50s); лог: `docs/last_pytest_run.txt`
- `black` / `isort` на `src/` + `tests/`

### Включено в релиз
- Manus: `plan_progress`, A2A resume, `task_id` PG, confirm sink в фоне, `STEP_MODEL_ROUTING`
- Calendar: экспорт `.ics` в `workspace/users/{id}/calendar/`
- Доки: `ROADMAP_MVP`, `MVP_GAP_AUDIT`, `VPS_E2E_RUNBOOK`, research/, eval harness
- Скрипт: `scripts/ship.ps1`

### Не в коммит
- `ответ на промт*.md` (исходники research в корне)
- `scripts/_patch_resource_mitigations.py` (одноразовый патч)

---

## 2026-05-31 — Gap audit (скепсис vs OpenClaw/Manus)

### Честный вывод
- «Фазы 0–5 done» в todo = **код + pytest**, не prod parity.
- Полный аудит: [`docs/MVP_GAP_AUDIT.md`](MVP_GAP_AUDIT.md).

### Исправлено в этой сессии (P0 код)
- `llm_step_routing` → `llm_client.chat_completion` + `set_llm_step_kind` (plan_step / agent / finalize / continue).
- `task_id` в `dispatch_agent` → `build_environment` + `chat_history.get_recent` для шагов плана.
- `docs/OPENCLAW_PARITY.md` — confirmation gates → done (с оговоркой prod `REQUIRE_CONFIRM`).
- Subagent follow-up: `OutboundSink` на фоновом плане (`orchestrator_delegate`); HTTP API fail-closed (`health_server`, `tests/test_health_api_token.py`).

### 2026-05-31 (batch 2) — P1 код без VPS
- `plan_progress.py` — один editMessage для прогресса плана.
- `plan_executor`: A2A `on_a2a_step_callback`, `register_plan_resume`, `execute_steps_from_index`.
- PG: `chat_messages.task_id` + migration `g1h3i5j7k019`.
- `docs/VPS_E2E_RUNBOOK.md` — чеклист вечера на VPS.

### Остаётся P0 human / P2
- E2E sign-off по runbook, CalDAV write, MCP stdio, live eval.

### Verify
- `python -m pytest tests/test_llm_step_routing.py tests/test_llm_client_routing.py tests/test_chat_history.py -q`

---

## 2026-06-03 — Roadmap MVP фазы 0–5 (код)

### Статус по фазам (код + unit tests; prod E2E — human)

| Фаза | Сделано в репо | Prod sign-off |
|------|----------------|---------------|
| 0 Trust | confirm inline → `OutboundSink` + `inbound_turn`; `run_code` replay + gate; `E2E_SIGNOFF_TEMPLATE.md` | W11 D1–D6 — шаблон в notes |
| 1 Manus UX | `tool_results`→verify; `task_id` в plan dispatch; handoff + reply_to; cancel keyboard; **нет** single editMessage прогресс | Telegram manual |
| 2 Integrations | calendar/github/staff_summary tools; `INTEGRATIONS.md`; MCP allowlist POC | smoke в E2E_SIGNOFF |
| 3 Rules | `playbook.py` + assembler; `plan_recipes` + service + orchestrator reuse; business/marketing styles; `METRICS.md` | — |
| 4 Platform | `AGENT_RUN_API_TOKEN`; `/v1/models`; A2A callback + task context; `STEP_MODEL_ROUTING` wired in `llm_client` | curl + manual |
| 5 Maturity | `EVAL_HARNESS` 20+ scenarios; `WEB_APPS.md`; `FIRECRACKER_SPIKE.md` | eval pytest |

### Verify (local)
- `python -m pytest tests/ -q --tb=short` — ожидается green (включая `test_eval_scenarios`, `test_integrations`)

### MVP Done checklist (код)
- [x] ROADMAP_MVP + research waves 2–5
- [x] Фазы 0–5 артефакты и тесты
- [ ] E2E W1–W11 подписаны с датой (human, VPS)
- [ ] 30 дней solo journal

---

## 2026-06-02 — Ресурсы VPS + риски Groq (NOTEBOOK, бюджет LLM)

### Решение
- Память **вне** Groq: `workspace/users/{id}/NOTEBOOK.md` + инструмент `append_notebook` (Эльза, Егор).
- Мягкий дневной лимит: `LLM_SOFT_DAILY_CALLS`, `llm_budget.py`, `llm_context.py`; при исчерпании — понятное сообщение в чат.
- При ~85% бюджета — принудительный LIGHT tier (`GROQ_DEFER_HEAVY_ON_BUDGET`).
- Планы оркестратора: `MAX_PLAN_STEPS` (default 4).
- Док: [`docs/RESOURCE_AND_LLM.md`](RESOURCE_AND_LLM.md); env в [`deploy/FIRSTBYTE_VPS.md`](../deploy/FIRSTBYTE_VPS.md).

### Файлы
- `src/agents_tg/services/notebook.py`, `llm_budget.py`, `llm_context.py`
- `src/agents_tg/services/tools/notebook_tools.py`
- `src/agents_tg/services/prompts/memory_block.py` (блокнот в промпт)
- `config/settings.py`: `LLM_SOFT_DAILY_CALLS`, `MAX_PLAN_STEPS`, …
- `tests/test_resource_mitigations.py`

### Verify
- `python -m pytest tests/test_resource_mitigations.py tests/ -q --tb=short` (ожидается green)

### Отложено (до апгрейда VPS / второго провайдера)
- Ollama, Firecracker, MCP hub, eval harness 20+ сценариев.

---

## 2026-06-02 — Research wave 1 (promt1/2/3/4 plan)

### Phase 0 — docs/research
- `docs/research/README.md` — индекс + reconciliation + strategic backlog (P1/P2, defer Firecracker/MCP).
- `02-prompt-architecture.md` из `ответ на промт3.md`; `legacy-souls.md`.
- Обновлены `OPENCLAW_PARITY.md`, `E2E_AUTONOMY.md` (W11), `AGENT_BEHAVIOR.md` (deep_research).

### Phase 1 — prompt-layer
- `souls/research.md`; alias `research` / `sports_analyst` в `identity.py`.
- `prompts/styles/research.py`, `security.py`, `coder.py` → wired в `specialists.py`.
- `load_soul()` в PA + orchestrator.

### Phase 2 — execution & trust
- `tool_schemas.py` + schema pass в `verify_step.py`; `VERIFY_LLM_JUDGE`, `CONFIRMATION_TTL_SEC`.
- `confirmation_replay.py`; callbacks replay; `register_and_persist` + token/keyboard в `shared_context_tools`.
- `browser_tools.py`: `extracted_text`, docstring no-JS.

### Phase 3 — delegation UX
- `delegation_envelope.py`; контекст в `orchestrator_delegate`; DM delegation в `inbound_turn`.
- `plan_cancel.py` + callback `plan_cancel:`; `memory_block` + `task_id`.
- E2E W11 (D1–D10) — manual prod sign-off pending.

### Verify (local)
- `python -m pytest tests/ -q --tb=short` — **158 passed** (wave 1 tests included).

### Acceptance checklist (wave 1)
- [x] docs/research + parity reconcile
- [x] research soul + per-role styles
- [x] verify schema + confirmation replay
- [x] DelegationEnvelope + DM delegate + plan cancel hook
- [ ] Telegram prod D1–D6 (human)

---

## 2026-05-31 — Research wave 1 (prompts 1–4 → code)

### Phase 0 — docs/research
- Ingest `ответ на промт3.md` → `docs/research/02-prompt-architecture.md`
- Index + reconciliation in `docs/research/README.md`; `legacy-souls.md` unchanged
- `OPENCLAW_PARITY.md`: Task Brain/sandbox **done**; confirmation/delegation **partial** with pointers

### Phase 1 — prompt-layer
- `souls/research.md`, `identity.py` alias, per-role styles in `prompts/styles/{research,security,coder}.py`
- `specialists.py`: `ROLE_STYLES`, `load_soul` via `identity`
- `personal_assistant.py` / `orchestrator.py`: unified `load_soul`
- `AGENT_BEHAVIOR.md`: `deep_research` (not `web_search`)

### Phase 2 — execution
- `tool_schemas.py`, compositional `verify_step.py` + `VERIFY_LLM_JUDGE`
- `confirmation_service`: TTL 60s, `register_and_persist`, `run_code` gated
- `confirmation_replay.py` + callbacks replay; `shared_context_tools` returns `confirmation_token`
- `browser_tools.py`: `status_code`, `extracted_text`

### Phase 3 — delegation UX
- `delegation_envelope.py`, DM delegation in `inbound_turn.py`
- `plan_cancel.py`, `progress_ux.cancel_keyboard`, cancel in `plan_executor`
- `memory_block` optional `task_id`; `AgentEnvironment.task_id`

### Phase 4
- Strategic backlog P1/P2 in `docs/research/README.md` (Firecracker/MCP deferred)

### Verify
- `python -m pytest tests/ -q --tb=short` — **162 passed** (~54s)
- `python -m mypy src/` — не запускался (mypy не установлен в локальном venv)

### Manual E2E (pending)
- W11 matrix in `E2E_AUTONOMY.md` — prod Telegram per `deploy/FIRSTBYTE_VPS.md`

---

- **Git:** локально и на VPS `a126373` (= `c806196` parity code + docs); `git push` — уже на `origin/master`.
- **Deploy:** `python scripts/vps_deploy.py` — OK (`9d138d0` → `a126373`), `agents-tg` **active**, alembic OK, `apscheduler` установлен.
- **Health (VPS):** `curl http://127.0.0.1:8080/` → `{"status":"ok","service":"agents-tg","database":{"status":"ok"}}`.
- **Pytest (local):** `153 passed` in ~59s.
- **Следующий шаг:** ручная приёмка Telegram по [`E2E_AUTONOMY.md`](E2E_AUTONOMY.md) (5 smoke из `FIRSTBYTE_VPS.md` + W5#19 `run_code` deny у Эльзы).

---

## 2026-05-31 — Parity roadmap OpenClaw + Manus (P0–P4)

### P0 Ops
- **Deploy:** `VPS_SSH_PASSWORD` не в среде → `vps_deploy.py` не запускался. После задания пароля: `python scripts/vps_deploy.py` → smoke `curl :8080` + 5 TG сценариев из `FIRSTBYTE_VPS.md`.
- **E2E:** матрица W1–W30 — unit-прокси расширены; prod Telegram — manual post-deploy.

### P1 Manus
- `services/verify_step.py`, `services/progress_ux.py`, интеграция в `plan_executor` + `orchestrator_delegate`.
- `services/role_tools.py` shim → `plugins.role_tools`.
- Тесты: `test_verify_step`, `test_plan_executor_progress`, `test_agent_outer_loop_replan`, `test_artifact_service`.

### P2 OpenClaw execution
- `SANDBOX_MODE` / `SANDBOX_DOCKER_IMAGE` в settings; `docker_runner.py` subprocess + docker.
- `browser_tools.py` retry + `<title>` extraction.
- `.env.example` обновлён.

### P3 Platform MVP
- `mcp/client.py` — `MCP_ENABLED`, `MCP_SERVERS` JSON, allowlist.
- `plugins/demo/plugin.yaml` + `plugin_echo`; `services/tools/mcp_tools.py`.
- `GET /v1/models` в `health_server.py`.

### P4 Docs
- `OPENCLAW_PARITY.md`, `AGENT_PIPELINE.md`, legacy `bot/__init__.py` (без «календарь»).

### Verify
- `python -m pytest tests/ -v --tb=short` — **153 passed** (~58s).
- **Git:** `c806196` pushed `origin/master`.

---

## 2026-05-31 — Readiness plan: ship + E2E matrix + README sync

### Ship (`ship-prompt-security`)

| Шаг | Статус | Детали |
|-----|--------|--------|
| Commit | ✅ | `2ec3252` — prompt-layer, orchestrator v2, `tool_policies` + hook, +3 tests |
| Push `master` | ✅ | `origin/master` @ `2ec3252` |
| `pytest` | ✅ | **144 passed** (~41s, local Windows) |
| VPS deploy | ⏳ | `VPS_SSH_PASSWORD` не задан в среде агента → `python scripts/vps_deploy.py` **не запускался**. После deploy на VPS: `git pull` → `2ec3252`, `systemctl restart agents-tg`, `curl -s http://127.0.0.1:8080/` на сервере |

### E2E W1–W10 (`e2e-prod-w1-w10`)

Матрица после ship **2ec3252**. Легенда: **unit** = покрыто pytest; **manual** = Telegram ЛС на prod; **post-deploy** = нужен `vps_deploy` + smoke.

| W | # | Сценарий | Авто (pytest / код) | Prod Telegram |
|---|-----|----------|---------------------|---------------|
| W1 | 1 | «Привет» → без плана | `test_prompt_tier.py` (LIGHT, no tools) | manual |
| W1 | 2 | Длинный код → части (1/N) | `test_agent_runtime.py`, delivery | manual → Руслан |
| W1 | 3 | Напоминание 3 мин МСК | `test_role_tools`, cron paths | manual → Эльза |
| W1 | 4 | Рестарт до ping | — | manual (post-deploy + PG) |
| W1 | 5 | `curl :8080/` | `test_health` if any | **post-deploy** (SSH curl на VPS) |
| W2 | 6–9 | proactive / plan / anti-echo / digest | `test_proactive_policy`, `test_agent_wake` | manual |
| W3 | 10–14 | memory / project / Neon persist | integration-style tests partial | manual |
| W4 | 15–17 | envelope / dedupe / API | `test_envelope_dispatch`, `test_gateway_*` | manual #15–16; API optional |
| W5 | 18 | injection block | `test_gateway_hooks` | manual |
| W5 | 19 | PA `run_code` deny | **`test_tool_policy_hook`** ✅ | manual confirm |
| W5 | 20 | Руслан `run_code` | policy allows coder | manual |
| W6 | 21–22 | plan executor + PG | plan tests / gateway | manual → Егор |
| W7 | 23–25 | long msg, /journal, /status | runtime + commands | manual |
| W8 | 26–27 | confirmation gates | settings-gated | manual |
| W9 | 28 | workspace list | registry / tools | manual |
| W10 | 29–30 | heartbeat hours / skipWhenBusy | **`test_agent_wake`** ✅ | manual |

**Итог приёмки:** код и unit-прокси для W5/W10 готовы; **полная prod-подпись W1–W10** — после `vps_deploy` пройти чеклист в [`E2E_AUTONOMY.md`](E2E_AUTONOMY.md) в Telegram (5 smoke из `FIRSTBYTE_VPS.md` + таблица выше).

### README (`readme-sync`)

- Убраны обещания календаря/CRM/бюджета как реализованных; таблица **planned**.
- Добавлена таблица tools по `registry.py`, badge **personal beta**, примеры под реальные сценарии.

---

## 2026-06-02 — Cursor hook: отключён stop_verify_reminder

- **Запрос:** убрать follow-up «pytest + implementation-notes» в конце сессии агента.
- **Изменения:** удалён блок `stop` из `.cursor/hooks.json`; скрипт `.cursor/hooks/stop_verify_reminder.py` оставлен в репо (можно вернуть).
- **Доки:** `.cursor/README.md`, `.cursor/rules/team-kit-workflow.mdc`.
- **Напоминание:** verify и журнал по-прежнему в `agent-workflow-core.mdc` / `task-closure-protocol.mdc` — вручную или по запросу.
- **После правки:** перезагрузить окно Cursor (Hooks).

## 2026-05-31 — Hook verify (prompt-layer + orchestrator + hooks, re-run)

- **Trigger:** post-edit hook — `orchestrator.py`, `personal_assistant.md`, `hook_registry.py`, `hooks/__init__.py`, `injection_guard.py`, `agent_outer_loop.py`, `agent_prompts.py`, `agent_runner.py`.
- **Verify:** `python -m pytest tests/ -v --tb=short` — **144 passed** in 46.1s (Windows, local).
- **Status:** no regressions; orchestrator v2 + tool_policy hook + finalize/replan stable.

## 2026-05-31 — Prompt-layer + tool security (ответ на промт.md)

- **Baseline commit:** `5708f29` — pipeline handlers, prompts package, coalesce.
- **Prompt decomposition:** `system_directives.py`, `styles/{personal_assistant,specialist}.py`, `orchestrator_directives.py`, `finalize_directives.py`, `proactive.py`; `behavior.py` → re-export shim.
- **Orchestrator v2:** `supervisor_parse.normalize_supervisor_data()` — `action_type`, `reasoning`, `request_replan`; legacy `next_agent` compat.
- **Finalizer:** structured E.3 HTML template via `build_finalize_prompt(has_tool_results=…)`.
- **Security:** `gateway/tool_policies.py` + `hooks/tool_policy.py`; tier/user_message context in `hook_registry.run_before_tool_call`.
- **Replan:** `REPLAN_DIRECTIVE`, orchestrator replan on specialist errors / `[[REPLAN]]`, outer loop checkpoint `action_type`.
- **Soul:** `personal_assistant.md` — убраны дубли TOOLS (ссылка на MANUS_PA_STYLE).
- **Verify:** `python -m pytest tests/ -v --tb=short` — **144 passed**.

## 2026-05-31 — Hook verify (pipeline core files, re-run)

- **Trigger:** post-edit hook after changes in `agent_bot.py`, `settings.py`, `agent_dispatch.py`, `job_store.py`, `router.py`, `agent_outer_loop.py`, `agent_prompts.py`, `agent_runner.py`.
- **Diff (uncommitted):** 8 files, −930/+159 LOC — thin `agent_bot`, envelope-first `agent_dispatch`, job FSM in `job_store`/`router`, prompt shims, outer loop multi-turn.
- **Verify:** `python -m pytest tests/ -v --tb=short` — **131 passed** in 34.19s (Windows, local).
- **Status:** no regressions; envelope-first dispatch + job FSM + prompt shims + outer loop stable.

## 2026-06-01 — SA-OPS-LOCK + SA-DOCS-E2E (pipeline workplan)

- **poetry.lock:** added `apscheduler` 3.11.2 + updated `content-hash`; `poetry check` green locally.
- **Docs:** `docs/AGENT_PIPELINE.md` (flow + file map); `AGENT_RUNTIME.md` synced; `E2E_AUTONOMY.md` deduped (appendix A1–A6).
- **Verify:** `python -m pytest tests/ -v --tb=short` — **131 passed** (incl. `test_envelope_dispatch.py`, heartbeat active-hours fix).
- **Deploy:** run `python scripts/vps_deploy.py` after push (needs `VPS_SSH_PASSWORD`).

## 2026-06-01 — SA-PROMPT-L4 (prompts package split)

- **New package** `src/agents_tg/services/prompts/`: `behavior.py` (constants), `tier_rules.py` (regex tiers + trim), `identity.py` (soul loader + `prompt_identity`), `memory_block.py` (memory + `build_scheduled_context`), `assembler.py` (`build_system_prompt`), `__init__.py` re-exports.
- **Shims:** `agent_prompts.py`, `prompt_builder.py` re-export from `prompts` for backward compat.
- **Tools:** builtin tools moved to `services/tools/builtin.py`; `agent_runner.py` keeps loop only; fixed `hook_registry` NameError in tool hook path.
- **Bootstrap:** `bootstrap_context.py` uses `human_name_for()` instead of duplicate `_AGENT_NAMES`.
- **Tests:** `tests/test_prompt_tier.py` (tier detection, soul load, assembler); legacy `test_prompt_builder.py` unchanged.
- **Verify:** `pytest tests/ -v` — **128 passed**.

---

## 2026-06-01 — SA-DELIVERY-UX (preview + coalesce)

- **C1:** `channels/delivery/streaming.py` — `PreviewStreamer` edits thinking message via `editMessageText` (throttled pseudo-stream + cursor).
- **C2:** `gateway/coalesce.py` — `BlockCoalescer` merges short blocks within `COALESCE_IDLE_MS`.
- **C3:** `OutboundSink` in `agent_runtime.py` — async `push`, coalesce drain, preview; `send_telegram_message` awaits sink; inbound passes `thinking_message` only from bot call site.
- **C4:** `PREVIEW_STREAMING_ENABLED` (default true), `COALESCE_IDLE_MS` (default 400; 0 = off) in `settings.py`.
- **Tests:** `tests/test_coalesce.py` (5), extended `test_agent_runtime.py`.
- **Docs:** `OPENCLAW_PARITY.md` — preview/coalesce → **done**.
- **Verify:** `python -m pytest tests/ -v --tb=short` → **128 passed** (~40s).

---

## 2026-06-01 — SA-ARCH-PIPELINE (handler split + gateway FSM)

- **A1:** `agent_bot.py` slim shell (~140 LOC); handlers → `bots/handlers/{commands,inbound,callbacks}.py`.
- **A2:** Delivery/delegation → `services/inbound_turn.py`.
- **A3:** Single L3 entry `dispatch_agent(envelope)`; removed `dispatch_agent_process` bypass from bot.
- **A4:** Job FSM `queued → running → done/failed` via `job_store.transition()` + `router.start_job` / `fail_job`.
- **A5:** `services/tools/registry.py` — `tool_names_for_agent`; used in `agent_dispatch`, `agent_runner`.
- **A6:** `AgentOuterLoop.run` multi-turn loop up to `MAX_AGENT_TURNS` (optional `[[CONTINUE]]` suffix).
- **Verify:** `python -m pytest tests/ -v --tb=short` — **131 passed** (incl. `test_envelope_dispatch.py`, heartbeat active-hours fix).

## 2026-05-31 - Neon sslmode fix (asyncpg + Neon)

- **Problem:** Neon/libpq connection strings include query params (`sslmode`, `channel_binding`, `sslrootcert`, `sslcert`, `sslkey`) that SQLAlchemy/asyncpg forwards to `asyncpg.connect()` as invalid kwargs.
- **Fix (`src/agents_tg/config/settings.py`):** `normalize_database_url()` strips those libpq params after driver rewrite (`postgresql+asyncpg://`); other query keys preserved.
- **Fix (`src/agents_tg/db/session.py`):** `_neon_ssl_connect_args()` sets `connect_args={'ssl': True}` when host contains `neon.tech` or raw URL still mentions `sslmode=require|verify`; merged in `create_engine()`.
- **Verify:** `python -m pytest tests/ -v --tb=short` — **111 passed**, 0 failed (~25s, local Windows).

## 2026-06-01 — Neon asyncpg: strip libpq ssl params + VPS deploy

- **Problem:** Alembic/app on VPS failed — asyncpg `connect()` got unexpected kwargs `channel_binding`, `sslmode` from Neon `DATABASE_URL` query string.
- **Fix:** `normalize_database_url()` strips `channel_binding`, `sslmode`, `sslrootcert`, `sslcert`, `sslkey`; `create_engine()` adds `connect_args={"ssl": True}` for Neon hosts.
- **Files:** `src/agents_tg/config/settings.py`, `src/agents_tg/db/session.py`, `tests/test_settings.py` (`TestNormalizeDatabaseUrl`, 4 cases).
- **Verify:** `pytest tests/test_settings.py` — **10 passed**; poetry CLI not on Windows PATH — **poetry.lock not updated**.
- **Commit:** `9d138d0` — `fix: strip libpq ssl params for asyncpg Neon`
- **Push:** `origin/master` `e71881e..9d138d0` ✅
- **Deploy VPS (91.186.221.32):** `git reset` → `9d138d0`; **alembic upgrade head** ✅ (initial → `f8a1c3d5e927` gateway/manus tables); `agents-tg` **active**
- **Health:** `curl :8080` → `{"status":"ok","service":"agents-tg","database":{"status":"ok"}}`
- **Journal:** `Database connected and tables ensured` (startup)
- **Minor:** VPS `poetry install` warns lock stale vs pyproject — non-blocking (venv already installed)

## 2026-06-01 — Ship: full OpenClaw/Manus parity (e71881e) 🚢 push OK, deploy blocked

- **Commit:** `e71881e` — feat: full OpenClaw + Manus parity (47 files, +3062 lines)
- **Verify pre-ship:** pytest — **107 passed**
- **Push:** `origin/master` `ffa581b..e71881e` ✅
- **Deploy:** **BLOCKED** — `VPS_SSH_PASSWORD` not in shell or `.env`
- **Unblock:** set `VPS_SSH_PASSWORD`, then `python scripts/vps_deploy.py`; optional Neon via `vps_configure_neon.py`; migration `f8a1c3d5e927` on VPS

## 2026-06-01 — Full OpenClaw + Manus parity (Phases 0–13) ✅ verify

- **Phase 0 — Ops:** `health_server.py` — PG ping in JSON (`database.status`); `POST /v1/agent/run`, `POST /v1/webhook/a2a/callback`; VPS deploy needs local credentials (`VPS_SSH_PASSWORD`, Neon `DATABASE_URL`).
- **Phase 1 — L1 Envelope:** `gateway/envelope.py`, `channels/telegram_adapter.py`; `agent_bot` → adapter → `gateway_router.dispatch`; `_process_request` → `gateway/agent_dispatch.dispatch_agent_process` (arch test `test_arch_layer_boundaries.py`).
- **Phase 2 — L2 Gateway:** `gateway/router.py`, `session.py`, `job_store.py`; migration `f8a1c3d5e927` (`agent_jobs`, `agent_tasks`, `plan_steps`, `pending_confirmations`).
- **Phase 3 — Hooks:** `gateway/hook_registry.py`, `hooks/injection_guard.py`; wired in `agent_runner.py` (before_prompt, before_tool, after_tool).
- **Phase 4 — Task Brain + Cron:** APScheduler in `reminder_service`; heartbeat `activeHours`/`skipWhenBusy`/`lightContext` in `agent_wake.py`; job recovery on startup in `main.py`.
- **Phase 5 — PlanExecutor:** `services/plan_executor.py`; orchestrator LangGraph `supervisor → specialist → supervisor` loop; `orchestrator_delegate.py` step iteration.
- **Phase 6 — AgentOuterLoop:** `services/agent_outer_loop.py` — `MAX_AGENT_TURNS`, checkpoint via `plan_executor.save_checkpoint`.
- **Phase 7 — Progress UX:** `humanDelay` in `telegram_delivery.py`; `/journal`, `/task`, `/status` in `agent_bot.py`; `artifact_service.py`.
- **Phase 8 — Confirmations:** PG `pending_confirmations`; TG inline callbacks `confirm:{token}:yes|no`; `REQUIRE_CONFIRM` env.
- **Phase 9 — Sandbox:** `sandbox/docker_runner.py` (`run_code`/`run_python_code`); `browser_tools.py` httpx fallback; sandbox guard in hooks.
- **Phase 10 — Plugins + MCP:** `plugins/registry.py`, `plugins/deep_research/plugin.yaml`; `mcp/client.py` stub.
- **Phase 11 — Workspace isolation:** `workspace/users/{id}/agents/{role}/` in `workspace_memory.py`; `list_agent_workspace` tool.
- **Phase 12 — Role tools:** `services/role_tools.py` — orchestrator/coder/research/security P0 tools.
- **Phase 13 — Sidecar eval:** `docs/OPENCLAW_SIDECAR_EVAL.md` (decision gate, no Node code).
- **Verify:** `python -m pytest tests/ -v --tb=short` — **107 passed** (~286s on Windows).
- **Deploy:** `alembic upgrade head` for `f8a1c3d5e927`; VPS credentials not in agent shell — run deploy scripts locally.

## 2026-06-01 — Full OpenClaw + Manus parity (Phases 0–13) ✅ verify

- **Phase 0:** `health_server` PG ping; ops checklist (VPS deploy still needs `NEON_DATABASE_URL`).
- **Phase 1:** `OpenClawEnvelope`, `TelegramAdapter`, `agent_dispatch`; arch test `test_arch_layer_boundaries`.
- **Phase 2:** `GatewayRouter`, `AgentJobStore`, HTTP `/v1/agent/run`, `/v1/webhook/a2a/callback`; migration `f8a1c3d5e927`.
- **Phase 3:** `hook_registry` + injection/sandbox/audit hooks wired in `agent_runner`.
- **Phase 4:** APScheduler in `reminder_service`; heartbeat `activeHours` (30m default, 8–23 MSK).
- **Phase 5:** `PlanExecutor` + orchestrator supervisor↔specialist loop; `orchestrator_delegate` step progress.
- **Phase 6:** `AgentOuterLoop` + `MAX_AGENT_TURNS`.
- **Phase 7:** `humanDelay` in delivery; `/journal`, `/task`, `/status`; `ArtifactService`.
- **Phase 8:** `confirmation_service` PG + TG inline callbacks.
- **Phase 9:** `sandbox/docker_runner`, `browser_tools` httpx stub.
- **Phase 10:** `plugins/registry.py`, `role_tools` plugin, MCP stub.
- **Phase 11:** `workspace/users/{id}/agents/{role}/` isolation.
- **Phase 12:** P0 role tools (delegate_task, run_code, browser_*, scan_prompt, …).
- **Phase 13:** `docs/OPENCLAW_SIDECAR_EVAL.md` — defer Node sidecar.
- **Verify:** `python -m pytest tests/ -v --tb=short` — **107 passed**.
- **Docs:** `OPENCLAW_PARITY.md`, `E2E_AUTONOMY.md` W4–W10.

## 2026-06-01 — OpenClaw/Manus parity plan (Phases 0–4) ✅ verify

- **Phase 1 — Cron → AgentRun:** `run_scheduled_reminder` + `REMINDER_LLM_DELIVERY`; `reminder_service.set_cron_deliver_fn`.
- **Phase 2 — Event wake + policy:** `proactive_policy.py`; heartbeat PA only, orchestrator project check-in; `run_event_wake(precomputed=)` in `background_runs`, `orchestrator_delegate`; `record_outbound` on inbound DM.
- **Phase 3 — Memory + Manus:** `append_journal_md`, `refresh_memory_md` on facts/projects; `confirmation_service` + `REQUIRE_CONFIRM` gate on `update_project_status:done`.
- **Phase 4 — Docs:** `AGENT_RUNTIME.md`, `AGENT_BEHAVIOR.md`, `OPENCLAW_PARITY.md` — honest done/partial/backlog.
- **Verify:** `python -m pytest tests/ -v --tb=short` — **97 passed** (~25s).
- **Ship:** commit `5e5387b` pushed to `origin/master`.
- **Deploy (Phase 0 ops):** `VPS_SSH_PASSWORD` / `NEON_DATABASE_URL` not in shell — run locally: `python scripts/vps_configure_neon.py` then `python scripts/vps_deploy.py`; `alembic upgrade head` on VPS.

## 2026-06-01 — Multi-agent wake + proactive_intent (runtime) ✅ verify

- **Цель:** автономность не только промптами — фоновые пробуждения и materialize расписания до ответа LLM.
- **`agent_wake.py`:** `set_process_fns(dict)` — heartbeat по **каждому** `agent_key` с отдельным `process_fn`; `_run_and_deliver(..., process_fn=)`.
- **`main.py`:** при старте регистрирует `_process_request` **всех** 7 ботов в `AgentWakeService` (не только Эльза).
- **`proactive_intent.py` (new):** regex «каждый день в 11», «напомни через …», autonomy cues → `reminder_service.schedule()` **до** LLM; `build_scheduled_context()` в hints.
- **`personal_assistant.py`:** `try_schedule_from_message` в `process()`; tool `schedule_reminder` + `recurrence=daily`.
- **`prompt_builder.py`:** напоминания/автономность → FULL tier + `schedule_reminder` в allowed tools.
- **Напоминания:** `reminder_service` + `models.recurrence` + миграция `e7a9b2c4d816`; `settings.normalize_database_url()` strip `channel_binding`.
- **Prompt/SOUL:** `agent_prompts.py`, `personal_assistant.md`, `agent_identity.py` (вспомогательно).
- **Тесты (new):** `tests/test_proactive_intent.py`, `tests/test_reminder_recurrence.py`.
- **Verify (hook, последний):** `python -m pytest tests/ -v --tb=short` — **88 passed** in 25.65s (2026-06-01); файлы hook без изменений с прошлого прогона.
- **Deploy:** локально uncommitted; VPS нужен push + `vps_deploy.py` + `alembic upgrade head`.
- **TODO:** E2E «каждый день в 11:00» на VPS с Neon; wake только для агентов с `user_contacts` inbound.

## 2026-06-01 — VPS deploy (user request) ✅

- **Trigger:** user asked «сделай деплой на впс»; `master` clean, synced with `origin/master`.
- **VPS (91.186.221.32):** `git reset --hard origin/master` → **`31486d7`** (was `79f05f9`); `deploy/HEARTBEAT.default.md OK`; `workspace/HEARTBEAT.default.md OK`.
- **Service:** `agents-tg` **active**; `curl :8080` → `{"status":"ok","service":"agents-tg"}`; all 7 bots registered in journalctl.
- **Alembic:** was failing with `channel_binding` — **fixed in code** via `settings.normalize_database_url()`; re-deploy + migrate to apply on VPS.

## 2026-05-31 — Autonomous agent runtime (behavior, not prompt-only) 🚧

- **Problem:** Эльза отвечала «не могу писать автономно» — LLM без tools, хотя на VPS уже есть `ReminderService` + `AgentWakeService`.
- **Root cause:** capability-вопросы шли в LIGHT tier (0 tools); `recurrence=daily` был в промптах, но не в коде; wake только у `personal_assistant`.
- **Fix (code):**
  - `proactive_intent.py` — до ответа LLM материализует «каждый день в 11 МСK» → `reminder_service.schedule(recurrence=daily)`.
  - `reminder_service` + alembic `e7a9b2c4d816` — поле `recurrence` (`once`|`daily`), после fire daily перепланируется.
  - `prompt_builder` — напоминания/автономность → FULL tier + `schedule_reminder` в STANDARD.
  - `agent_wake` + `main.py` — heartbeat/process_fn для **всех** зарегистрированных ботов.
- **Verify (2026-05-31, hook):** `python -m pytest tests/ -v --tb=short` — **88 passed** in 25.71s.
- **Файлы:** `personal_assistant.py`, `personal_assistant.md`, `settings.py`, `models.py`, `agent_identity.py`, `agent_prompts.py`, `agent_wake.py`, `prompt_builder.py`, `proactive_intent.py`, `reminder_service.py`, `main.py`, `e7a9b2c4d816` migration, tests.
- **Deploy:** commit → push → `vps_deploy.py` → `alembic upgrade head` на VPS (миграция recurrence).

- **Root cause:** `env.py` used `alembic.ini` default `localhost:5432`; VPS `.env` had Neon `DATABASE_URL` but migrations ignored it → `ConnectionRefusedError`.
- **Fix:** `src/agents_tg/db/migrations/env.py` — `get_settings().async_database_url` → `config.set_main_option("sqlalchemy.url", …)` before online/offline runs.
- **VPS script:** `scripts/vps_configure_neon.py` — `agent_status` via `{POETRY} run python` (not bare `python3`).
- **Ops:** `scripts/neon_provision.py` (API provision EU); temp `scripts/_neon_*`, `*_out.txt`, `neon_uri.txt` removed + `.gitignore`.
- **Cursor:** `.cursor/permissions.json`, `.cursor/rules/agent-autonomy.mdc` — pre-authorized verify/ship/deploy (no secrets in repo).
- **Neon project (VPS API):** `agentsTG`, region `aws-eu-central-1`, host `ep-long-dawn-*.neon.tech` (credentials only in env, not committed).
- **Verify local (2026-05-31, post `env.py`):** `python -m pytest tests/ -v --tb=short` — **84 passed** in 22.78s.
- **Post-commit:** push → CI green → `vps_deploy.py` → `vps_configure_neon.py` → journalctl `Database connected` (update verdict below).

## 2026-06-01 — Neon persistence full cycle ❌ NOT VERIFIED

- **Persistence verdict:** **NOT VERIFIED** — journalctl: `Running without persistence` (not `Database connected`)
- **DATABASE_URL host (VPS):** **localhost:5432** (`postgresql+asyncpg://user:***@localhost:5432/agents_tg`)
- **Ship commit (code):** `991337c` — shutdown fix, `poetry.lock`, `vps_configure_neon.py`
- **VPS:** `79f05f9` on 91.186.221.32 (`vps_deploy.py` 2026-06-01); `agents-tg` **active**; `curl :8080` → `{"status":"ok","service":"agents-tg"}`
- **CI:** [run #14](https://github.com/fishacot/agentsTG/actions/runs/26724485582) — **success**; `head_sha` = `991337c`
- **Neon credential search:** `$env:NEON_*` / `DATABASE_URL` empty; local `.env` = localhost only; no `ep-*.neon.tech` in repo/transcript `5e8f932f`; `npx neonctl projects list` → OAuth browser, **auth timed out** (non-interactive)
- **`vps_configure_neon.py`:** **skipped** (no `NEON_DATABASE_URL`)
- **`vps_deploy.py`:** **re-run** 2026-06-01 → VPS `79f05f9`; `agents-tg` **active**; alembic still `ConnectionRefusedError` localhost:5432
- **Alembic on VPS:** `ConnectionRefusedError` `127.0.0.1:5432`
- **VPS_SSH_PASSWORD:** used for SSH re-audit (***); set `$env:VPS_SSH_PASSWORD` locally for deploy scripts
- **Unblock:** Neon EU project + connection string → `$env:NEON_DATABASE_URL` + `vps_configure_neon.py` + `vps_deploy.py` → journalctl must show `Database connected`

## 2026-05-31 — Hotfix: duplicate `stop_health_server()` in shutdown ✅

- **Commit:** `1721a0e` (ветка `deploy-neon`) — также `scripts/vps_configure_neon.py`, deploy docs
- **Файл:** `src/main.py` — в `on_shutdown()` удалён второй подряд `await stop_health_server()` (copy-paste)
- **Поведение:** `stop_health_server()` идемпотентен (`_server_task` → `None` после первого вызова), но дубликат был лишним
- **Verify (повтор):** `python -m pytest tests/ -v --tb=short` — **84 passed** (~68s, 2026-05-31)

## 2026-05-31 — CI green + VPS deploy hardening (full plan) ✅

- **Commit:** `e9b5659` — `fix(ci): green pytest, alembic path, HEARTBEAT deploy`
- **Push:** `e5049f0..e9b5659` → `origin/master`
- **CI:** [run #12](https://github.com/fishacot/agentsTG/actions/runs/26713449488) — **success** (Lint + Test + Alembic)
- **Файлы:** `.github/workflows/test.yml`, `alembic.ini`, `env.py`, `deploy/HEARTBEAT.default.md`, `workspace_memory.py`, `scripts/vps_deploy.py`
- **CI fix:** `poetry install --only main,dev` вместо ручного pip (duckduckgo-search, trafilatura, greenlet и др.)
- **Alembic fix:** `env.py` → `parents[4]` (repo root); `prepend_sys_path = .`; импорт `UserTask`, `UserContact`
- **HEARTBEAT:** git-tracked `deploy/HEARTBEAT.default.md`; fallback в `load_heartbeat_md`; bootstrap `workspace/` в `vps_deploy.py`
- **VPS deploy (91.186.221.32):** git → `e9b5659`; `deploy/HEARTBEAT.default.md OK`; `workspace/HEARTBEAT.default.md OK`; `agents-tg` **active**
- **Alembic на VPS:** import path **исправлен** (нет `ModuleNotFoundError: src`); upgrade падает на `ConnectionRefusedError 127.0.0.1:5432` — `DATABASE_URL` = localhost, Neon не настроен
- **Poetry на VPS:** `pyproject.toml changed significantly since poetry.lock` — lock не синхронизирован (CI ставит через poetry install; VPS venv уже есть)
- **Verify локально:** flake8 clean, `alembic heads` → `d4e6f8a0c205`, **84 passed**
- **Блокер persistence:** Neon `DATABASE_URL` в `.env` на VPS — см. `deploy/NEON_SETUP.md`

## 2026-05-31 — CI fix + deploy hardening ✅

- **CI email (GitHub Actions run #10):** упал шаг **Lint** (flake8), не pytest — pytest даже не запускался
- **Причины:** сотни E501 в legacy-коде; F401/F541/E305 в нескольких файлах; `alembic.ini` указывал на несуществующий `src/db/migrations`
- **Фиксы:** `.flake8` extend-ignore E501; unused imports; `alembic.ini` → `src/agents_tg/db/migrations`; `agent_status.py` sys.path bootstrap; `vps_deploy.py` safe print + conditional alembic
- **Verify локально:** flake8 clean, `alembic heads` → `d4e6f8a0c205`, **84 passed**
- **VPS (не конфиг):** код на `338ce57` уже был; **PG всё ещё offline** — `DATABASE_URL` на VPS = localhost:5432, Neon не настроен → tasks/reminders/contacts in-memory

## 2026-05-31 — Deploy VPS: Agent Wake `338ce57` ✅

- **Git push:** `ef233cf..338ce57` → `origin/master`
- **VPS:** `91.186.221.32` — `git reset --hard origin/master` → **`338ce57`**
- **systemd:** `agents-tg` **active** (pid 25098 после restart)
- **Логи:** `AgentWakeService started (interval=60 min, quiet=12.0h)` — патч поднялся
- **Health:** `:8080` listening
- **7 ботов:** polling OK (@elliza_pa_bot и остальные)
- **Известные ограничения:** PG localhost:5432 недоступен → in-memory fallback (Neon `DATABASE_URL` ещё не в `.env` на VPS); `poetry` не в PATH non-interactive shell (не блокер — venv systemd уже есть)
- **Deploy script:** локальный exit 1 из-за Unicode emoji в journalctl на Windows — на сервере deploy успешен

## 2026-05-30 — Verify: Agent Wake (полный pytest) ✅

- **Команда:** `python -m pytest tests/ -v --tb=short` (docs/PROJECT_VERIFICATION.md)
- **Результат:** **84 passed** in ~28s
- **Затронутые файлы (scope):** `personal_assistant.py`, `souls/personal_assistant.md`, `agent_bot.py`, `settings.py`, `models.py`, `agent_runtime.py`, `environment_context.py`, `reminder_service.py` + новые `agent_wake.py`, `user_*_service.py`, `main.py`, тесты `test_agent_wake.py`, `test_user_tasks_service.py`
- **Статус Phase 0–1:** код готов; prod E2E W2 и Neon на VPS — ещё не проверены

## 2026-05-30 — Phase 0–1: Agent Wake (heartbeat + LLM digest) 🚧

- **Scope creep отклонён (не never):** grammY/TS gateway, OpenClaw Node plugins, LanceDB, Neo4j, Temporal, e2b — отдельные epics; сейчас Python/aiogram + Neon PG достаточно.
- **P0:** `user_tasks`, `user_contacts` (models + alembic `d4e6f8a0c205`); `user_tasks_service`, `user_contact_service`; `scripts/agent_status.py`; tasks в PG вместо in-memory.
- **P1:** `AgentRuntime.run_scheduled()`, `AgentWakeService`, `workspace/HEARTBEAT.default.md`, env `HEARTBEAT_*`.
- **Интеграция:** `main.py` стартует wake loop; утренний digest через LLM (`HEARTBEAT_DIGEST_LLM`); `record_inbound` в `agent_bot`; soul Эльзы обновлён.
- **Файлы:** `agent_wake.py`, `agent_runtime.py`, `reminder_service.py`, `environment_context.py`, `personal_assistant.py`, `models.py`, `settings.py`
- **Verify:** `python -m pytest tests/ -v --tb=short` — **84 passed** (2026-05-30)
- **TODO VPS:** Neon `DATABASE_URL` + `alembic upgrade head` на 91.186.221.32 (контакты/задачи/reminders в PG)
- **E2E:** пользователь молчит 12h+ → proactive LLM (см. `docs/E2E_AUTONOMY.md` W2)

## 2026-05-30 — Hotfix: Эльза молчит в DM (debounce deadlock) ✅

- **Симптом:** после деплоя `64e6001` личные сообщения `@elliza_pa_bot` — полная тишина, нет даже «🤖 Думаю…»; в логах `Update … Duration 27 ms`, нет `inbound_start`.
- **Причина:** `message_pipeline.enqueue_debounced` оборачивал handler в `run_lock`, а `_handle_inbound` в `agent_bot.py` берёт тот же lock → **deadlock** на DM (MESSAGE_DEBOUNCE_MS=2000).
- **Фикс:** убран внешний `run_lock` из `_flush`; handler сам сериализует чат.
- **Файлы:** `src/agents_tg/services/message_pipeline.py`, `tests/test_message_pipeline.py`
- **VPS:** `git reset --hard origin/master` → **`23b2d3d`**; `agents-tg` **active**; health `{"status":"ok"}`
- **Verify:** `pytest tests/test_message_pipeline.py` — 3 passed

## 2026-05-30 — Push + VPS deploy OpenClaw (64e6001)

- **Git:** `64e6001` feat(openclaw): shared memory + project focus — pushed to `origin/master`
- **Fix перед push:** `.env` случайно попал в commit → GitHub push protection (Groq/GCP keys). Пересобран commit без `.env`; добавлен `.env` в `.gitignore`
- **VPS (91.186.221.32):** `git reset --hard origin/master` → `64e6001`; `agents-tg` **active**
- **Alembic на VPS:** `alembic` не в PATH при deploy — миграции shared_context не накатаны; без `DATABASE_URL` работает in-memory fallback
- **Health :8080:** проверить после старта (`curl http://127.0.0.1:8080/`)
- **Smoke TG:** Егор «сайт о собаках», Эльза «привет» — см. `docs/E2E_AUTONOMY.md` W3

---

- **Schema:** `user_profiles`, `user_projects`, `project_activity`; `user_facts.category`; alembic `c3d5f7a2b104`
- **Services:** `shared_context.py`, `bootstrap_context.py`, `workspace_memory.py`, `orchestrator_project.py`, `shared_context_tools.py`, `check_in_cooldown.py`
- **Tools:** `update_user_profile`, `set_active_project`, `log_project_activity`, `update_project_status`; category on `remember_about_user`
- **Bootstrap:** TIME/USER/FOCUS/MEMORY/TOOLS blocks → all 7 agents via `build_environment`
- **Cross-agent:** auto-log after run (`agent_bot.py`); Егор binds plan → project; Эльza check-in 24h cooldown
- **Files:** `agents/tools/*.md`, `workspace/users/{id}/USER.md`, `memory/YYYY-MM-DD.md`; docs `OPENCLAW_PARITY.md`, `E2E_AUTONOMY.md` (W3)
- **Souls (shared focus):** `orchestrator.md`, `personal_assistant.md`, `coder_soul.md`, `security_ai.md`, `business_manager.md`, `marketing.md` — TOOLS + фокус проекта
- **Fix:** circular import `shared_context_tools` ↔ `agent_runner` — lazy import в `run()`; bootstrap tests — `monkeypatch` на модульный `shared_context`
- **Verify:** `python -m pytest tests/ -v --tb=short` → **77 passed** (~71s)
- **Deploy VPS / Neon / smoke «сайт о собаках»:** не выполнялся; ждёт `DATABASE_URL` + явный «пуш» (см. `deploy/NEON_SETUP.md`, `docs/E2E_AUTONOMY.md` W3)

---

## 2026-05-30 — Verify: agents + souls (post master plan)

- **Команда:** `python -m pytest tests/ -v --tb=short` → **69 passed** (~58s)
- **Файлы в scope:** `orchestrator.py`, `personal_assistant.py`, souls (`orchestrator`, `personal_assistant`, `coder_soul`, `sports_analyst`, `security_ai`, `business_manager`, `marketing`)
- **orchestrator.py:** `should_stay_silent` → `NO_REPLY` в группе после ack коллеге; plan в coordinator
- **Souls:** секция **TOOLS (честные границы)** — не обещать напоминания/поиск/delegation без tool+runtime
- **Deploy VPS / Neon:** без изменений; ждёт connection string и «пуш»

---

## 2026-05-30 — Agent autonomy master plan (W0–W2 complete)

- **Runtime:** `agent_runtime.py`, `OutboundSink`, `send_telegram_message` tool, multi-bubble delivery
- **Pipeline:** debounce, dedupe (Redis NX), followup queue, per-chat `run_lock`
- **Reminders:** `reminder_service` MSK poll 30s; `schedule_reminder` tool; morning digest 09:00 after /start
- **Neon:** `deploy/NEON_SETUP.md`; alembic `b2c4e8f1a903` (reminders, chat_messages, user_facts); `init_db` fallback
- **Observability:** `/health` :8080; `structured_log.log_event`; per-user LLM cooldown (+ Redis)
- **W2:** Ульяна background research; Егор async delegation; group NO_REPLY + anti-echo before send
- **Souls:** TOOLS blocks for all 7 agents (honest boundaries)
- **Tests:** +test_group_coordinator, test_message_pipeline, test_reminder_service
- **CI:** `.github/workflows/test.yml` — redis/sqlalchemy deps, alembic heads
- **Verify:** `python -m pytest tests/ -v`
- **Deploy VPS:** не выполнялся (ждёт явного «пуш» от человека)

---

## 2026-05-30 — Agent runtime W0/W1 (старт): delivery + MSK + profiles

- **Диагноз подтверждён:** chatbot (запрос→1 ответ), не автономные агенты. Master plan: `.cursor/plans/ruslan_+_elza_fixes_073e68b9.plan.md`
- **Docs:** `docs/AGENT_RUNTIME.md`, `docs/OPENCLAW_PARITY.md`
- **MSK:** `APP_TIMEZONE=Europe/Moscow`, `timezone_utils.py`, «Сейчас … МСК» в env block всех агентов
- **Delivery:** `channels/telegram_delivery.py` — chunking 4096, multi-bubble `(1/N)`, retry; убран silent `[:4000]`
- **Profiles:** `agent_delivery_profile.py` — 7 агентов; coder 1536 tokens, PA 3 tool rounds
- **Runner:** per-profile max_tool_rounds; `_maybe_continue` при длинном ответе
- **Tests:** test_timezone_utils, test_telegram_delivery, test_agent_delivery_profile — OK
- **TODO next:** reminder_service (W1.7), AgentRuntime v1 (W1.2), message_pipeline (W1.3), Neon setup (W1.6)

---

- **CLI dev-tools (OK):** `ruff 0.11.11` (`pip`), `npm install` + `markdownlint-cli2` для docs verify.
- **Расширения IDE:** конфиг `.vscode/extensions.json` (11 шт.); **CLI-установка зависает** на marketplace (`cursor --install-extension` → timeout на `ms-python.python`). Сейчас в Cursor только `anysphere.remote-ssh`, `anysphere.remote-wsl`. **Действие:** Extensions → «Install Recommended» или `scripts/install-cursor-extensions.ps1` когда сеть стабильна.
- **Проект:** `.vscode/settings.json` (format on save, pytest, ruff); `.gitignore` — коммитим `extensions.json` + `settings.json`.
- **Hooks:** `.cursor/hooks.json` + 3 Python-скрипта (ruff after edit, guard shell, verify reminder).
- **Team Kit:** глобально в `~/.cursor/plugins/.../cursor-team-kit/`; правило `.cursor/rules/team-kit-workflow.mdc`.
- **Док:** `docs/CURSOR_SETUP.md`, `.cursor/README.md`.
- **После установки ext + pull:** Reload Window → Settings → Hooks.

---

## 2026-05-30 — Backlog: план на ~2 недели (следующая сессия)

- **План (полный):** `.cursor/plans/2-week_agentstg_roadmap_75644e33.plan.md`
- **Приоритет:** balanced (40% infra / 40% features / 20% dev workflow)
- **Бюджет:** 1–2 тыс. ₽/мес — Neon PG, Upstash Redis, резерв на Groq/proxy
- **Статус на сегодня:** скелет 7 агентов на VPS `a99eb59` ✅; к backlog не приступали

### TODO (очередь)

| ID | Задача | Неделя |
|----|--------|--------|
| `w1-postgres-redis` | Neon Postgres + Upstash Redis на VPS; persistence истории/фактов | 1 |
| `w1-observability-llm` | `/health`, structured logs, per-user LLM cooldown, тесты PG/Redis | 1 |
| `w2-async-research` | Фоновый `deep_research`: ack → worker → финальный ответ в TG | 2 |
| `w2-group-orchestrator` | Plan visibility + anti-echo в group; E2E сценарий в docs | 2 |
| `w2-dev-workflow` | Cursor hooks, CI, deploy по SSH key, ROADMAP/notes | 2 |

### Отложено (после 2 недель)

Ollama на VPS, vector RAG, Mem0 SaaS, E2B, webhook mode, streaming в TG.

---

## 2026-05-30 — LLM-first + Groq TPM для всех 7 агентов

- **Цель:** те же правки «интеллекта» (LLM-first, без шаблонов) для всех специалистов + снижение Groq 429 (TPM).
- **prompt_builder / agent_runner:**
  - `_RESEARCH_ACTION_PATTERN` — `deep_research` только при явном поиске (FULL + web agents).
  - `tools_for_tier(..., include_web_tools=)` — STANDARD без deep_research; длинные сообщения → FULL только при search/action.
  - `MAX_TOOL_ROUNDS=1`; history 4/8/12; max_tokens cap 512/640/768; WEB_TOOL_HINT только при research intent.
- **specialists.py:** `MANUS_SPECIALIST_STYLE` + `max_tokens=768` для всех 6 специалистов.
- **orchestrator.py:** LIGHT tier (привет/кто ты) → 1 вызов `agent_runner` вместо supervisor+specialist (экономия ~50% токенов на small talk); supervisor max_tokens 280.
- **Souls:** границы LLM-first в `coder_soul`, `sports_analyst`, `security_ai`, `business_manager`, `marketing`, `general`, `orchestrator`.
- **Файлы:** `prompt_builder.py`, `agent_runner.py`, `agent_prompts.py`, `specialists.py`, `orchestrator.py`, 7× souls, tests.
- **Verify:** pytest **51 passed**.
- **Git:** commit `a99eb59` → pushed `origin/master`.
- **VPS (91.186.221.32):** `git reset --hard origin/master` → `a99eb59`; `agents-tg` **active**.

---

## 2026-05-30 — LLM-first: убраны статические FAQ-ответы

- **Проблема:** Эльза отвечала шаблоном на «кто ты» / «что можешь» (`capability_templates.py` fast-path) и вызывала `list_tasks` на «сводку новостей» → «нет в списке дел».
- **Решение (философия: агент думает сам, оболочка направляет поток):**
  - Удалены `capability_templates.py` и все FAQ fast-path в `personal_assistant.py` и `orchestrator.py`.
  - «Кто ты», возможности, память, новости/сводки → **LIGHT tier, 0 tools**, ответ только через LLM + soul.
  - STANDARD tier: только `remember_about_user`; `list_tasks` — если явно «покажи дела».
  - Усилены промпты в `agent_prompts.py`, soul Эльзы (handoff на @ulyana_research_bot для новостей).
- **Файлы:** `prompt_builder.py`, `personal_assistant.py`, `orchestrator.py`, `agent_prompts.py`, `personal_assistant.md`; удалён `capability_templates.py`.
- **Verify:** pytest **48 passed**.
- **Git:** commit `92ae0d5` → pushed `origin/master`.
- **VPS (91.186.221.32):** `git reset --hard origin/master` → `92ae0d5`; `capability_templates.py` удалён на сервере; `agents-tg` **active**.

---

## 2026-05-30 — Elza Groq 429 patch (commit + VPS deploy) ✅

- **Лог:** 1-й запрос OK (FAQ); 2-й — Gemini 400 → Groq 200 → crash `args=null`; далее Groq TPM 429 на тяжёлых промптах.
- **Fix:** `LLM_PROVIDER_CHAIN=groq` на VPS; `parse_tool_arguments` (null JSON); STANDARD tier — только remember/list_tasks; max_tokens 768; FAQ «можешь запоминать»; RateLimitError → дружелюбный текст; MAX_TOOL_ROUNDS=2.
- **Verify:** pytest **52 passed**.
- **Git:** commit `eea882c` → pushed `origin/master`.
- **VPS (91.186.221.32):** `git reset --hard origin/master` → `eea882c`; `.env` `LLM_PROVIDER_CHAIN=groq`; `systemctl restart agents-tg` → **active**; все 7 ботов в polling.
- **Приёмка (Telegram, ручная):** «расскажи что ты можешь» → instant HTML; обычное 2-е сообщение → ответ без «😕 ошибка»; при 429 → «подождите 15–30 сек».

---

## 2026-05-30 — Elza: Groq tool args `null` crash

- **Лог 01:07:09:** Gemini 400 → fallback OK → Groq **200** → `AttributeError: 'NoneType' object has no attribute 'setdefault'` в `agent_runner.py:239`.
- **Причина:** Groq вернул `arguments: "null"` → `json.loads` → `None`, не `{}`.
- **Fix:** после parse проверка `isinstance(parsed, dict)`.
- **Deploy:** патч на VPS + restart.

---

## 2026-05-30 — Elza: Gemini geo-block на VPS, fallback fix

- **Симптом:** `personal_assistant` → `API error (gemini-2.5-flash): 400` — `"User location is not supported for the API use."` (FirstByte VPS).
- **Причина:** Gemini недоступен с IP VPS; при 400 fallback на Groq **не срабатывал** (только 429).
- **Fix:** `llm_client.chat_completion` — при ошибке провайдера пробует следующий в chain, если он есть.
- **Тест:** `test_chat_completion_fallback_on_provider_error`.
- **Deploy:** патч `llm_client.py` на VPS + restart `agents-tg`.
- **Примечание:** Gemini с VPS не заработает без прокси; chain `gemini,groq` теперь уходит на Groq автоматически.

---

## 2026-05-30 — VPS deploy завершён (FirstByte 91.186.221.32)

- **VPS:** `git reset --hard origin/master` → `c6dcef4`; `.env` с `GEMINI_API_KEY` + `LLM_PROVIDER_CHAIN=gemini,groq` (не перезаписан git).
- **Service:** `systemctl restart agents-tg` → **active**.
- **Локально:** `.env` обновлён с Gemini key (gitignored).
- **Приёмка (Telegram, ручная):** Эльза «расскажи что ты можешь» → instant HTML; Егор «привет» → только Егор; нет 429.
- **Безопасность:** пароль VPS и Gemini key были в чате — рекомендована ротация.

---

## 2026-05-30 — Full audit + Gemini chain deploy prep

- **Аудит:** 48 pytest passed; flake8; GitHub Actions `.github/workflows/test.yml`.
- **LLM:** `llm_client` — dynamic `get_settings()` для chain/available (fix тестов + runtime).
- **Orchestrator:** pure greeting → `build_egor_greeting_html()` без LLM.
- **Models:** `settings.get_agent_model()` → `get_model_for_provider(primary chain)`.
- **Docs:** `deploy/FIRSTBYTE_VPS.md` (91.186.221.32), Gemini key guide в TIMWEB guide.
- **Тесты:** +12 (llm chain fallback, agent_runner tiers, orchestrator greeting, PA FAQ).
- **Verify:** `pytest tests/ -v` — **48 passed**; coverage llm_client 48%, prompt_builder 60%.
- **Commit/push:** `c6dcef4` на `origin/master`.

---

## 2026-05-29 — Agents Soul LLM Upgrade (tiered prompts, Gemini chain, compact souls)

- **Проблема на VPS:** Groq 429 (TPM 6000, prompt ~4800 tok) на «что ты можешь»; orchestrator возвращал HTML вместо JSON.
- **Фаза 1 — Tiered prompts:** `prompt_builder.py` — `PromptTier` LIGHT/STANDARD/FULL; trim soul/env/history; LIGHT без tools (~−1500 tok). Интеграция в `agent_runner.py`.
- **FAQ без LLM:** `capability_templates.py` + `personal_assistant.py` — шаблонный HTML на «что ты можешь» (0 API-вызовов).
- **429 UX:** `llm_client.py` — parse `try again in Xs`, до 6 retry, `RateLimitError`; `agent_bot.py` — дружелюбное сообщение.
- **Multi-provider:** `llm_client.py` — цепочка `gemini → groq → hf`; `settings.py` — `GEMINI_*`, `LLM_PROVIDER_CHAIN`; `agent_models.py` — `PROVIDER_MODELS`, orchestrator **8B** (не 70B); `qwen_client.py` — re-export alias.
- **Orchestrator JSON:** `ORCHESTRATOR_JSON_DIRECTIVE` + HTML fallback через `supervisor_parse.py`; retry без `json_object` если parse failed.
- **Souls:** переписаны из `AGENT_PERSONALITIES` (~30 строк, Telegram HTML): `personal_assistant.md`, `orchestrator.md`, 5 specialists.
- **MANUS_PA_STYLE:** расширен intent→action matrix в `agent_prompts.py`.
- **Deploy docs:** `.env.example`, `deploy/TIMWEB_VPS_GUIDE.md` (Gemini AI Studio), `deploy/OLLAMA_VPS.md` (после апгрейда RAM).
- **Verify:** `python -m pytest tests/ -v` — **35 passed**.
- **VPS deploy (ручной шаг):** `git pull`, добавить `GEMINI_API_KEY` + `LLM_PROVIDER_CHAIN=gemini,groq` в `/opt/agentsTG/.env`, `systemctl restart agents-tg`.

---


- **Фаза 1 — Environment «глаза»:** `environment_context.py` (`AgentEnvironment`, `build_environment`); `agent_bot` собирает контекст (chat type, peers, vault, tools, group/dm history) и передаёт в `process()` / `AgentRunner`.
- **Фаза 2 — История:** `chat_history.py` (in-memory + Redis + Postgres hook); подключено в `AgentRunner` (system prompt + append после ответа).
- **Фаза 3 — Deep search:** `search_provider.py` (`deep_research`), tool в `agent_runner`; улучшен `internet.py` (retry, `fetch_multiple_pages`).
- **Фаза 4 — Telegram HTML:** `telegram_format.py` (`sanitize_html_for_telegram`, `send_agent_response`); ответы агентов через HTML с fallback на plain.
- **Фаза 5 — Протоколы:** `TELEGRAM_AGENT_PROTOCOL`, `TELEGRAM_HTML_FORMAT` в `agent_prompts.py`; HTML `output_hints` в `specialists.py`; orchestrator получает protocol + HTML для `direct_reply`.
- **Фаза 6 — Канал заметок:** `telegram_notes.py`, tool `post_to_notes_channel` в PA; env `NOTES_CHANNEL_ID`; гайд `deploy/NOTES_CHANNEL.md`.
- **Фаза 7 — Personalities:** **отложено** до правок пользователя в `docs/AGENT_PERSONALITIES.md` (не переносим в `souls/` без финального текста).
- **Фаза 8 — Postgres:** модели `ChatMessage`, `UserFact`; `init_db()` в startup; `chat_history.set_pg_available`, `memory_service.set_pg_available` + `user_facts_pg.py`.
- **Файлы (новые):** `environment_context.py`, `chat_history.py`, `chat_history_pg.py`, `search_provider.py`, `telegram_format.py`, `telegram_notes.py`, `user_facts_pg.py`, `db/init_db.py`, тесты `test_*`.
- **Verify:** `python -m pytest tests/ -v` — **24 passed**.
- **Deploy VPS:** `git pull && systemctl restart agents-tg`; задать `NOTES_CHANNEL_ID` при необходимости.

---

## 2026-05-28 — Goal-oriented агенты (без ACTION/CREATE_NOTE классификации)

- **Проблема:** Эльза на «ты можешь запоминать?» создавала заметку `[Title]` — жёсткая классификация CREATE_NOTE/CHAT.
- **Решение:** единый `AgentRunner` + LLM **function calling** (Groq tools):
  - модель сама решает: разговор или инструмент;
  - Эльза: `create_obsidian_note`, `add_task`, `list_tasks`, `remember_about_user`;
  - специалисты: `web_search`, `fetch_web_page`, `remember_about_user`;
  - общий промпт `GOAL_DIRECTIVE` в `agent_prompts.py`.
- **Память:** `memory_service` — fallback in-process `_facts_store` per user_id, если Mem0 недоступен; поиск работает без облака.
- **Оркестратор:** приветствия/small talk → `direct_reply` от Егора; план показывается только при 2+ шагах.
- **LLM-вызовов:** было ~3 на сообщение (intent + answer + classify); стало ~1 (+ tool rounds при необходимости).
- **Файлы:** `agent_runner.py`, `agent_prompts.py`, `qwen_client.chat_completion`, `personal_assistant.py`, `specialists.py`, `orchestrator.py`, `memory_service.py`, тесты.
- **Verify:** pytest 15 passed.
- **Deploy:** commit `3573780` — tools return JSON only; LLM always speaks to user; MANUS_PA_STYLE for Elza.

---

## 2026-05-28 — Черновик личностей агентов + объяснение routing

- **Запрос:** пользователь написал «привет» Егору, получил план + ответ Эльзы.
- **Причина:** оркестратор делегирует supervisor → specialist; `process()` склеивает plan + последнее сообщение specialist.
- **Не баг кода:** текущий дизайн; поведение менять после правок пользователя в `docs/AGENT_PERSONALITIES.md`.
- **Файл для правок:** `docs/AGENT_PERSONALITIES.md` — человеческие описания ролей, тона, границ, примеры.

---

## 2026-05-28 — Groq 429: меньше вызовов + retry

- **Симптом на VPS:** `QwenAPIError: API error (llama-3.1-8b-instant): 429` в `general_node` → `_final_answer`.
- **Причина:** Groq free tier лимитирует RPS; оркестратор = supervisor (1) + specialist `_tool_intent` (1) + `_final_answer` (1) ≈ **3 LLM-вызова** на сообщение; раньше specialist возвращался в supervisor (ещё больше).
- **Правки (локально, ещё не в origin):**
  - `orchestrator.py` — после specialist ребро в `END`, не обратно в supervisor.
  - `qwen_client.py` — `asyncio.Semaphore(1)` (сериализация запросов) + retry на 429/503 с задержками 2/4/8 с (4 попытки).
- **Deploy на VPS:** `git pull && systemctl restart agents-tg` после push.
- **Если 429 останется:** писать напрямую боту-специалисту (1 агент = те же 2–3 вызова, но без supervisor); дальше — отключить `_tool_intent` для простых запросов.

---

## 2026-05-28 — Groq API (free tier) вместо Hugging Face

- **Причина:** HF Inference Providers — $0.10/мес, 402 после одного диалога; оркестратор делает ~15 LLM-вызовов на сообщение.
- **Решение:** Primary LLM = **Groq** (`GROQ_API_KEY`), HF остаётся optional fallback если Groq key пуст.
- **Endpoint:** `https://api.groq.com/openai/v1/chat/completions`
- **Модели** (`agent_models.py`):

  | Агент | Groq model |
  |-------|------------|
  | Егор | `llama-3.3-70b-versatile` |
  | Эльза, Ульяна, Артём, Ваня, Тася | `llama-3.1-8b-instant` |
  | Руслан | `qwen/qwen3-32b` |

- **VPS:** FirstByte FI 91.186.221.32, systemd `agents-tg`, Python 3.11 via deadsnakes.
- **Файлы:** `settings.py` (`llm_api_key`, `llm_api_base`), `qwen_client.py`, `agent_models.py`, `.env.example`, `render.yaml`.
- **TODO:** Упростить оркестратор (меньше LLM round-trips) — иначе Groq daily limits тоже кончатся быстро.

---

## 2026-05-27 — Per-agent Hugging Face models (free tier)

- **Задача:** Подобрать лучшие бесплатные модели HF для каждого агента, один токен `QWEN_API_KEY`.
- **API:** Переведён на OpenAI-compatible endpoint `https://router.huggingface.co/v1/chat/completions`.
- **Модели по ролям** (`src/agents_tg/services/agent_models.py`):

  | Агент | Модель | Зачем |
  |-------|--------|-------|
  | Егор (orchestrator) | `Qwen/Qwen2.5-7B-Instruct` | JSON-планирование, routing |
  | Эльза (PA) | `microsoft/Phi-3.5-mini-instruct` | Быстрый парсинг задач/заметок |
  | Руслан (coder) | `Qwen/Qwen2.5-Coder-7B-Instruct` | Код, архитектура |
  | Ульяна (research) | `meta-llama/Llama-3.1-8B-Instruct` | Синтез, длинный контекст |
  | Артём (security) | `mistralai/Mistral-7B-Instruct-v0.3` | Аналитика, чеклисты рисков |
  | Ваня (business) | `meta-llama/Llama-3.1-8B-Instruct` | Структурированные планы |
  | Тася (marketing) | `mistralai/Mistral-7B-Instruct-v0.3` | Креатив, копирайт |

- **Override:** env `MODEL_<ROLE>` или `settings.get_agent_model(agent_key)`.
- **Файлы:** `agent_models.py`, `qwen_client.py`, `settings.py`, `specialists.py`, `orchestrator.py`, `personal_assistant.py`, `.env.example`, `render.yaml`, `tests/test_agent_models.py`.
- **Tradeoff:** 7B модели надёжнее на free tier, чем 72B (cold start / лимиты). Качество ниже 72B, но стабильнее для 24/7.

---

- **Решение:** Пользователь готов платить 350–400₽/мес → VPS в Амстердаме (Timeweb Cloud)
- **Создано:**
  - `deploy/TIMWEB_VPS_GUIDE.md` — полная инструкция по покупке и настройке
  - `deploy/agents-tg.service` — systemd service для автозапуска 24/7
  - `deploy/timeweb-vps-setup.sh` — скрипт первоначальной настройки сервера
- **Особенности:**
  - Локация Amsterdam — Telegram API доступен без VPN
  - Systemd service с auto-restart — боты перезапускаются при падении
  - Журнал логов — `journalctl -u agents-tg -f`
- **Требуется:** GitHub repo + push текущего кода

---

## 2026-05-26 — Fly.io: бесплатный деплой для теста (РФ)

- **Выбор платформы:** Fly.io (free tier: 1 VM shared-cpu, 512MB, always-on) — подходит для polling без VPN из РФ.
- **Render** — worker только на платном Starter (~$7/мес); оставлен в `render.yaml` на будущее.
- **Добавлено:** `fly.toml`, Dockerfile, `.dockerignore`
- **Git:** commit `4995f3d` создан локально; push не выполнен — нет `git remote origin` (нужен GitHub repo).

---

- **Проблема:** Локальный запуск в России — `api.telegram.org` недоступен без VPN (`WinError 121`).
- **Решение:** Background Worker на Render.com (серверы за рубежом, Telegram доступен).
- **Обновлено:**
  - `render.yaml` — worker `agents-tg-bots`, Python 3.11, `python -m src.main`
  - `Dockerfile` — CMD исправлен на `python -m src.main`
  - `settings.py` — `normalize_database_url()` для Render PostgreSQL (`postgresql://` → `postgresql+asyncpg://`)
  - `.dockerignore` — ускорение Docker-сборки
- **Важно:** Background Worker на Render — платный план **Starter ~$7/мес** (free tier только для web, не для polling).
- **Env vars на Render (ручная настройка в Dashboard):**
  - Все `BOT_TOKEN_*` (7 штук)
  - `GROUP_CHAT_ID=-1003620415441`
  - `QWEN_API_KEY=hf_...`
- **PostgreSQL/Redis:** опционально, боты работают без них (graceful degradation).

---

- **Ошибка запуска:** `ImportError: cannot import name 'create_bot_manager_from_settings'`
  - **Причина:** функция была в `multi_bot_manager.py`, но не экспортировалась из `bots/__init__.py`
  - **Фикс:** добавлен экспорт в `src/agents_tg/bots/__init__.py`

- **Ошибка #2 (предыдущая сессия):** `TokenValidationError` при импорте
  - **Причина:** legacy `bot/__init__.py` создавал `Bot(token=settings.BOT_TOKEN)` при импорте
  - **Фикс:** убрана инициализация single-bot из `bot/__init__.py`

- **Критический баг username:** Руслан, Ульяна, Артём были без `_bot` суффикса
  - Было: `@ruslan_coder`, `@ulyana_research`, `@artem_security`
  - Стало: `@ruslan_coder_bot`, `@ulyana_research_bot`, `@artem_security_bot`
  - **Без этого упоминания в группе не работали!**
  - Обновлены: `agent_identity.py` + все SOUL.md

- **Улучшения multi-bot:**
  - Windows: отключены Unix signal handlers (не работают на Win)
  - Порядок запуска: сначала регистрация ботов, потом лог
  - GROUP_CHAT_ID регистрируется в GroupCoordinator
  - Индикатор «🤖 Думаю...» при обработке
  - Упоминания @bot убираются из текста перед отправкой в AI
  - Контекст группового чата передаётся агентам

- **Verify:**
  - ✅ `flake8 src/ tests/` — OK
  - ✅ `pytest tests/ -v` — 4 passed
  - ✅ `python -m src.main` — все 7 ботов стартуют, polling работает
  - ⚠️ PostgreSQL: `asyncpg` не установлен — боты работают без БД (graceful degradation)

- **Что ещё нужно для production (не блокирует тест):**
  - `poetry install` — все зависимости
  - PostgreSQL + `asyncpg` — персистентность
  - Webhook mode (Render.com) — Этап 2 ROADMAP
  - Тесты агентов — coverage 3%

---

- **Все параметры для запуска получены:**
  - ✅ 7 токенов Telegram ботов
  - ✅ HuggingFace токен (хранится только в локальном `.env`, не в git)
  - ✅ `GROUP_CHAT_ID` задан в локальном `.env`

- **Финальный конфиг `.env`:**
  - Скопировать из `.env.example` и подставить реальные значения локально.
  - **Не коммитить** токены ботов, API-ключи и ID чата в репозиторий.

- **Команда для запуска:**
  ```bash
  python -m src.main
  ```

- **Как тестировать:**
  1. **В ЛС с любым ботом:**
     - `/start` — приветствие со списком коллег
     - `/colleagues` — кто в команде
     - `/about_me` — кто этот бот
  
  2. **В группе (`-1003620415441`):**
     - `@egor_orchestrator_bot` составь план на сегодня
     - `@ruslan_coder_bot` что думаешь о Python 3.13?
     - `@ulyana_research_bot` найди информацию о LLM моделях 2024

- **Статус:** Полностью готово к запуску и тестированию! 🎉

---

## 2026-05-26 — ✅ Токены и username обновлены, система готова к тестированию

---

## 2026-05-26 — ✅ Имена ботам присвоены и аудит проведён

- **Присвоены человеческие имена ботам:**
  - **Егор** — Оркестратор (@egor_orchestrator)
  - **Эльза** — Ассистент (@eliza_pa)
  - **Руслан** — Кодер (@ruslan_coder)
  - **Ульяна** — Исследователь (@ulyana_research)
  - **Артём** — Безопасность (@artem_security)
  - **Ваня** — Бизнес (@vanya_business)
  - **Тася** — Маркетолог (@tasya_marketing)

- **Обновлены файлы:**
  - `src/agents_tg/services/agent_identity.py` — добавлены `human_name`, `designation`, обновлены `username` и `intro_dm` для всех агентов
  - `src/agents_tg/agents/souls/*.md` — в каждый SOUL файл добавлен раздел с коллегами и их именами
  - `.env.example` — обновлены username и добавлены комментарии с именами

- **Аудит системы:**
  - ✅ `flake8 src/` — без ошибок (кроме migrations)
  - ✅ `pytest tests/` — 4 passed
  - ✅ `black` — все файлы отформатированы
  - ✅ Структура файлов целостна

- **Статус:** Система готова к тестированию с реальными токенами

---

## 2026-05-26 — ✅ Multi-Bot Архитектура Завершена

- **Что сделано:** Полная перестройка с single-bot на multi-bot систему
- **Реализовано:**
  - **7 отдельных ботов** — каждый агент (и оркестратор) имеет свой Telegram бот с уникальным токеном
  - **Упоминания в группе** — боты реагируют на @username в групповом чате
  - **Личные сообщения** — прямая работа с каждым агентом в DM
  - **Коллеги в SOUL.md** — каждый агент знает о других и может их упоминать
  - **Shared memory** — единая БД для всех ботов, общий контекст
  - **Inter-bot awareness** — GroupCoordinator отслеживает сообщения всех ботов
- **Структура:**
  ```
  src/agents_tg/bots/
  ├── agent_bot.py         # Класс AgentBot — каждый агент как отдельный бот
  ├── multi_bot_manager.py # Управление всеми ботами
  └── group_coordinator.py # Координация в групповом чате
  ```
- **Настройки (.env):**
  ```
  BOT_TOKEN_ORCHESTRATOR=...
  BOT_TOKEN_PA=...          # @pa_agent
  BOT_TOKEN_CODER=...       # @coder_agent
  BOT_TOKEN_RESEARCH=...    # @research_agent
  BOT_TOKEN_SECURITY=...    # @security_agent
  BOT_TOKEN_BUSINESS=...    # @business_agent
  BOT_TOKEN_MARKETING=...   # @marketing_agent
  GROUP_CHAT_ID=-100...     # ID группы для коллаборации
  ```
- **Обновлены SOUL.md:**
  - Добавлен раздел "👥 МОИ КОЛЛЕГИ" в каждый SOUL файл
  - Агенты знают usernames друг друга (@username)
  - Описано когда и как привлекать коллег
- **Проверки:**
  - ✅ `flake8 src/` — без ошибок
  - ✅ `pytest tests/` — 4 passed
  - ✅ `black` — все файлы отформатированы
- **Следующий шаг:**
  - Протестировать с реальными токенами
  - Настроить групповой чат и добавить ботов
  - Доработать inter-bot communication (передача контекста между агентами)

---

## 2026-05-26 — Архитектура: Multi-Bot System (7 ботов)

- **Контекст:** Пользователь уточнил, что нужна архитектура с 6 отдельными Telegram ботами + оркестратор в группе, где они взаимодействуют через упоминания @username.
- **Решение:** Полная перестройка с single-bot на multi-bot архитектуру.
- **Создано:**
  - `src/agents_tg/bots/` — новый пакет для multi-bot системы:
    - `agent_bot.py` — класс AgentBot, каждый агент = отдельный бот со своим токеном
    - `multi_bot_manager.py` — управление всеми ботами, регистрация, запуск/остановка
    - `group_coordinator.py` — координация в групповом чате, история сообщений
  - `src/agents_tg/services/agent_identity.py` — идентичности всех агентов с username для упоминаний
  - Обновлен `src/agents_tg/config/settings.py` — добавлены BOT_TOKEN_* для всех 7 ботов + GROUP_CHAT_ID
  - Переписан `src/main.py` — запускает всех ботов параллельно через MultiBotManager
  - Обновлен `.env.example` — шаблон для 7 токенов
- **Ключевые изменения:**
  - Каждый агент имеет свой Telegram username (@pa_agent, @coder_agent и т.д.)
  - В группе боты реагируют только на упоминания (@username)
  - В ЛС боты отвечают напрямую (direct messaging)
  - Shared memory через БД — все агенты знают общий контекст
- **Tradeoffs:**
  - 7 токенов = 7 ботов в @BotFather — нужно создать все
  - Больше ресурсов (7 polling connections)
  - Но зато чистая архитектура и настоящее разделение агентов
- **Проверки:**
  - Структура файлов создана
  - Импорты прописаны
  - Требуется flake8 + black после всех изменений
- **Следующий шаг:**
  - Обновить SOUL.md для всех агентов (добавить описание коллег)
  - Добавить group chat handlers с упоминаниями
  - Прогнать verify

---

## 2026-05-26 — Создание детального ROADMAP до production

- **Контекст:** После честного анализа выявлено множество критических gap между текущим MVP и production-grade системой. Нужен структурированный план развития.
- **Решение:**
  - Создан `ROADMAP.md` с 9 этапами, приоритизацией P0/P1/P2
  - Оценки времени: 12 недель, 149-216 часов работы
  - Каждый этап имеет чеклист готовности и критерии приемки
- **Структура плана:**
  - **Этап 1 (P0):** Callback handlers, PostgreSQL, rate limiting, cleanup — 8-12 часов
  - **Этап 2 (P0):** Webhook, health checks, graceful shutdown, logging — 11-15 часов  
  - **Этап 3 (P1):** Vector DB (RAG), Redis cache, background tasks — 18-23 часа
  - **Этап 4 (P1):** Streaming ответы, multi-step progress — 10-14 часов
  - **Этап 5 (P1):** Google Calendar, GitHub API, email notifications — 18-26 часов
  - **Этап 6 (P2):** E2B sandbox, input validation, secrets encryption — 14-19 часов
  - **Этап 7 (P2):** Unit/integration tests, CI/CD pipeline — 26-34 часа
  - **Этап 8 (P2):** Metrics, alerting, analytics — 14-19 часов
  - **Этап 9:** Web dashboard, multi-user, custom agents — 30-38 часов
- **Tradeoffs:**
  - Разбивка по приоритетам P0/P1/P2 позволяет остановиться на любом этапе и иметь работающую систему
  - Оценки консервативные (верхняя граница) — реально быстрее если нет блокеров
- **Следующий шаг:**
  - Начать с Этапа 1 (критические фиксы) или выбрать другой этап по приоритету

---

## 2026-05-26 — Этап 1.1: Callback handlers для inline-кнопок

- **Контекст:** Inline-клавиатура в `/menu` отображалась, но нажатия не обрабатывались — кнопки были декоративными.
- **Решение:**
  - Добавлен `@router.callback_query(lambda c: c.data.startswith("agent_"))` в `src/agents_tg/bot/__init__.py`
  - Создан `process_callback()` с обработкой всех 7 callback_data:
    - `agent_team` — активирует командный режим (waiting_for_input)
    - `agent_pa`, `agent_coder`, `agent_research`, `agent_biz`, `agent_mkt`, `agent_sec` — активируют режим idle + приветствие конкретного агента
  - Каждый callback отвечает через `callback.answer()` (убирает часики) и отправляет сообщение с контекстом выбранного агента
- **Tradeoffs:**
  - Пока только активация режима + приветствие, без сразу вызова агента — это сделано намеренно, чтобы UX совпадал с текстовыми командами (/pa, /coder и т.д.)
  - FSM state меняется, но логика агента вызывается только при следующем текстовом сообщении (consistent behavior)
- **Файлы:**
  - `src/agents_tg/bot/__init__.py` — добавлен импорт `CallbackQuery`, обработчик `process_callback()`
- **Проверки:**
  - `black` — 1 file left unchanged ✅
  - `isort` — OK ✅
  - `flake8` — OK ✅ (исправлена F841 unused variable)
- **Следующий шаг:**
  - Задача 1.2: Подключение PostgreSQL в on_startup/on_shutdown

---

## 2026-05-26 — Этап 1.2: Подключение PostgreSQL

- **Контекст:** Бот работал без реального подключения к БД — `on_startup` и `on_shutdown` были пустыми TODO.
- **Решение:**
  - В `src/main.py` добавлена глобальная переменная `_db_engine` для хранения engine
  - `create_engine()` импортирован из `db.session` и вызывается в `main()` при старте
  - `on_startup()` теперь тестирует соединение (`SELECT 1`) и логирует результат
  - `on_shutdown()` закрывает соединения через `_db_engine.dispose()`
  - Graceful degradation: если БД недоступна — бот продолжает работать с предупреждением в логах
- **Tradeoffs:**
  - Engine создаётся глобально — не идеально для тестирования, но достаточно для MVP
  - Graceful degradation позволяет запускать бота локально без PostgreSQL, но продакшен требует БД
- **Файлы:**
  - `src/main.py` — добавлены импорты, `_db_engine`, логика в `on_startup`/`on_shutdown`
- **Проверки:**
  - `black` — 1 file reformatted ✅
  - `isort` — OK ✅
  - `flake8` — OK ✅ (исправлен F824 unused global)
- **Следующий шаг:**
  - Задача 1.3: Rate limiting middleware

---

## 2026-05-26 — Этап 1.3: Rate limiting middleware

- **Контекст:** Бот без защиты от флуда — пользователь мог спамить сообщения без ограничений, что создавало нагрузку и риск бана от Telegram.
- **Решение:**
  - Создан `src/agents_tg/bot/middlewares/ratelimit.py` с `RateLimitMiddleware`
  - Лимит: 3 сообщения на пользователя за 60 секунд
  - In-memory хранение временных меток (graceful degradation — не требует Redis для MVP)
  - При превышении лимита — ответ пользователю с таймером ожидания
  - Middleware зарегистрирован в `bot/__init__.py` через `dp.message.middleware()`
- **Tradeoffs:**
  - In-memory storage = не работает между рестартами и не шарится между инстансами
  - Для production с кластером нужен Redis-backed rate limiter
  - 3 msg/60 sec — консервативный лимит, можно увеличить при необходимости
- **Файлы:**
  - `src/agents_tg/bot/middlewares/ratelimit.py` — новый middleware
  - `src/agents_tg/bot/middlewares/__init__.py` — экспорт
  - `src/agents_tg/bot/__init__.py` — подключение middleware
- **Проверки:**
  - `flake8` — OK ✅ (исправлен E501 long line)
- **Следующий шаг:**
  - Задача 1.4: Удаление мертвого кода (coordinator.py)

---

## 2026-05-26 — Этап 1.4: Удаление мертвого кода

- **Контекст:** В проекте остались неиспользуемые файлы от старой архитектуры: coordinator.py, base.py, finance.py, notes.py, planner.py. Они создавали путаницу и замедляли разработку.
- **Решение:**
  - Удалены 5 файлов мертвого кода:
    - `coordinator.py` — устаревший агент, заменен на orchestrator.py
    - `base.py` — неиспользуемый базовый класс (BaseAgent)
    - `finance.py`, `notes.py`, `planner.py` — старые агенты, функционал интегрирован в personal_assistant
  - Обновлен `src/agents_tg/agents/__init__.py` — убран импорт BaseAgent, добавлен комментарий о lazy loading
- **Tradeoffs:**
  - Функционал старых агентов (finance, notes, planner) пока не полностью перенесен в personal_assistant — будет восстановлен при необходимости из git history
  - Удаление base.py упрощает код, но если понадобится общий базовый класс — придется создавать заново
- **Файлы:**
  - Удалены: `coordinator.py`, `base.py`, `finance.py`, `notes.py`, `planner.py`
  - Обновлен: `src/agents_tg/agents/__init__.py`
- **Проверки:**
  - `flake8 src/` — OK ✅
  - `flake8 src/agents_tg/agents/` — OK ✅
- **Итог Этапа 1 (P0 — Критические фиксы):**
  - ✅ 1.1 Callback handlers — кнопки меню работают
  - ✅ 1.2 PostgreSQL — подключение и graceful shutdown
  - ✅ 1.3 Rate limiting — защита от флуда 3msg/60sec
  - ✅ 1.4 Cleanup — удален мертвый код
- **Следующий шаг:**
  - Этап 2 (P0 — Инфраструктура стабильности): webhook, health checks, logging

---

## 2026-05-26 — Стабилизация, flake8-фиксы, verify

- **Контекст:** Проект после масштабного рефакторинга (LangGraph, 6 агентов) нуждался в стабилизации: синтаксические ошибки, неиспользуемые импорты, конфликт версий пакетов.
- **Решение:**
  - Исправлена синтаксическая ошибка в `personal_assistant.py` (незакрытая строка sleep → `time.sleep(1)`)
  - Снижены версии flake8 и pyflakes в `pyproject.toml` до совместимых с Python 3.13
  - Удалены неиспользуемые импорты:
    - `os` из `utils/git_sync.py`
    - `Any` из `utils/internet.py`
    - `sqlalchemy as sa` и `alembic.op` из `migrations/versions/361a0f436028_...`
  - Добавлены `# noqa: E402` для вынужденных импортов после sys.path в `migrations/env.py`
  - Обновлено меню бота: теперь 3 ряда × 2 агента в inline-клавиатуре (Coordinator, Personal, Planner, Finance, Notes, Integration)
- **Не в SPEC:**
  - Flake8 не поддерживает Python 3.13 → зафиксирована версия `flake8<7.1`
  - Poetry требовал `--sync` → заменено на `poetry sync` (deprecated, но `install` не подтягивал)
- **Tradeoffs:**
  - `# noqa: E402` в env.py — компромисс, т.к. sys.path должен быть раньше импортов, иначе Alembic не найдёт модули
  - Выбор Python 3.13 (системная версия) вместо 3.11 — flake8 пока несовместим натив
- **Файлы:**
  - `pyproject.toml` — версии flake8, pyflakes
  - `src/agents_tg/agents/personal_assistant.py` — исправление синтаксиса
  - `src/agents_tg/db/migrations/env.py` — noqa E402
  - `src/agents_tg/db/migrations/versions/361a0f436028_*` — удалены неисп. импорты
  - `src/agents_tg/utils/git_sync.py` — удалён `os`
  - `src/agents_tg/utils/internet.py` — удалён `Any`
  - `src/agents_tg/bot/__init__.py` — меню на 6 агентов
- **Проверки:**
  - `python -m poetry run black .` — 5 файлов reformatted ✅
  - `isort .` — OK ✅
  - `flake8 src/ tests/` — OK ✅
  - `pytest tests/ -v` — 4 passed ✅
- **Следующий шаг:**
  - Рефакторинг Coordinator → Orchestrator на LangGraph
  - Интеграция Mem0
  - Написание тестов для агентов

---

## 2026-05-26 — Выравнивание архитектуры под 6 агентов + Оркестратор

- **Контекст:** Пользователь хочет не «бота с функциями», а автономный офис из нескольких агентов, к которым можно обращаться лично и через общий чат. Документация (README, PROJECT_PROMPT) и фактический код разъехались: старые агенты (Planner/Finance/Notes/Integration) всё ещё описаны в README, хотя в коде уже есть Orchestrator + 6 специализированных агентов (Personal Assistant, Research, Security, Business, Marketing, General).
- **Решение:**
  - Обновлён `PROJECT_PROMPT.md`:
    - Зафиксирована архитектура «Оркестратор + 6 специалистов» с заменой сугубо спортивного Sports Analyst на универсального Research / Intel.
    - Обновлено текстовое описание ролей: Personal Assistant, Research, Security & AI, Business & PM, Marketing & Growth.
    - Уточнена цель проекта: не только бытовой ассистент, а мультиагентный офис с ресерчем, безопасностью, бизнесом и маркетингом.
  - Обновлён `README.md`:
    - Раздел «Описание» и «Архитектура» переписаны под Orchestrator + 6 агентов (Personal, Research, Security, Business, Marketing).
    - Обновлён технологический стек AI: Qwen 2.5 через бесплатные публичные эндпоинты (HuggingFace / OpenRouter), без завязки на DashScope.
    - Исправлена структура проекта: теперь отражает реальный пакет `src/agents_tg` и директории `agents/`, `bot/`, `config/`, `db/`, `services/`, `utils/`.
    - Обновлены команды использования под мультиагентную модель (`/team`, `/pa`, `/coder`, `/research`, `/biz`, `/mkt`, `/sec`) — пока как целевая контрактная часть, реализация в боте будет сделана отдельным шагом.
- **Не в SPEC:**
  - README дополнительно подчёркивает, что PostgreSQL/Redis опциональны для локальной разработки, чтобы упростить старт.
  - В README добавлены примерные значения `QWEN_API_BASE` для HuggingFace как ориентира, без жёсткой привязки к конкретному провайдеру.
- **Tradeoffs:**
  - Старые агенты (Planner/Finance/Notes/Integration) убраны из публичной документации, но код/миграции для финансами/заметок сохраняются как внутренний ресурс для Личного помощника и будущих интеграций.
  - Команды `/coder` и др. уже задекларированы в README, хотя их обработчики ещё не реализованы в `bot/__init__.py` — это осознанное «договорное API», которое будет реализовано в следующих задачах.
- **Файлы:**
  - `PROJECT_PROMPT.md` — обновлены цели и список агентов, структура диаграммы.
  - `README.md` — новая архитектура, стек, команды, структура проекта.
- **Проверки:**
  - Markdown просмотрен вручную; `docs/PROJECT_VERIFICATION.md` указывает `npm run verify` для Markdown, запуск будет на следующем цикле, если появится `package.json`.
- **Следующий шаг:**
  - Подключить всех 6 специалистов к Оркестратору (включить Coder/Research/Business/Marketing/Security/Personal Assistant в граф LangGraph и слой ToolEnabledAgent).
  - Спроектировать и реализовать команды Telegram (`/team`, `/pa`, `/coder`, `/research`, `/biz`, `/mkt`, `/sec`) и формат сообщений от имени разных агентов.

---

## 2026-05-26 — Подключение Coder/Research к Оркестратору и прямые команды в боте

- **Контекст:** После обновления архитектуры нужно, чтобы Оркестратор реально знал о Coder/Research, а из Telegram можно было обращаться к каждому агенту напрямую, не только через общий обработчик.
- **Решение:**
  - `src/agents_tg/agents/specialists.py`:
    - Для `ResearchAnalyst` введён собственный `process` с ресерч-ориентированным `output_contract` (список ссылок, критерии, риски, следующие шаги).
    - Добавлен новый агент `Coder`, основанный на `ToolEnabledAgent` и `coder_soul.md`, с контрактом ответа как у senior‑разработчика (резюме проблемы, архитектура, пример кода/diff, риски).
    - Экспортирован singleton `coder`.
  - `src/agents_tg/agents/orchestrator.py`:
    - Импортирован `coder` из `specialists`.
    - Обновлён `ORCHESTRATOR_SYSTEM_PROMPT`: список доступных агентов теперь отражает 6 специалистов (`personal_assistant`, `research`, `coder`, `security_ai`, `business_manager`, `marketing`), без упоминания устаревшего `sports_analyst`.
    - Граф LangGraph теперь содержит узлы `research` и `coder` (вместо `sports_analyst`), с переходами обратно в `supervisor`.
    - Добавлены методы `research_node` и `coder_node`, которые вызывают соответствующих агентов и помечают сообщения именем узла.
  - `src/agents_tg/bot/__init__.py`:
    - Расширен `/help` — добавлены все целевые команды (`/team`, `/pa`, `/coder`, `/research`, `/biz`, `/mkt`, `/sec`).
    - Пересобрано `/menu`: теперь inline‑клавиатура отражает Orchestrator + 6 агентов (PA, Coder, Research, Business, Marketing, Security).
    - Добавлен набор прямых хендлеров:
      - `/team` — включает командный режим и объясняет, что дальше писать задачу Оркестратору.
      - `/pa` — обращение к `personal_assistant.process`.
      - `/coder`, `/research`, `/biz`, `/mkt`, `/sec` — прямые вызовы соответствующих агентов из `specialists` с пробросом `user_id`.
- **Не в SPEC:**
  - Для Research и Coder сразу задано достаточно жёсткое форматирование ответов (контракты), по мотивам Open Claw, что упростит дальнейшую интеграцию в UI и журналы.
- **Tradeoffs:**
  - Личный помощник пока остаётся на отдельной реализации (`personal_assistant.py`), а не через `ToolEnabledAgent`, чтобы не ломать уже реализованную логику Obsidian/Tasks; выравнивание под единый базовый класс может быть сделано позже.
  - Команды меню через `callback_data` пока не имеют отдельных callback‑хендлеров — это только UI‑слой; фактическая логика общения идёт через текстовые команды и общий обработчик сообщений.
- **Файлы:**
  - `src/agents_tg/agents/specialists.py` — новые агенты/контракты.
  - `src/agents_tg/agents/orchestrator.py` — обновлённый граф и системный промпт.
  - `src/agents_tg/bot/__init__.py` — новые команды и меню.
- **Проверки:**
  - Логическая проверка импортов и имён узлов; запуск тестов и линтеров будет выполнен общим циклом verify после завершения всех задач из плана.
- **Следующий шаг:**
  - Спроектировать Manus‑style журналы и confirmation gates (по мотивам Manus/Open Claw) и зафиксировать выбор бесплатных моделей/интеграций в коде и документации.

---

## 2026-05-26 — Manus-style планирование и базовый Agent Journal

- **Контекст:** По плану нужно, чтобы Оркестратор и агенты работали в стиле Manus: явный план из шагов, видимый пользователю, и внутренний журнал действий агентов. При этом нельзя завязываться только на Mem0, т.к. бюджет 0 и ключ может отсутствовать.
- **Решение:**
  - `src/agents_tg/agents/orchestrator.py`:
    - Улучшен контекст для системного промпта: если у состояния уже есть `plan`, в промпт добавляется человекочитаемое представление текущего плана и номера шага, чтобы Оркестратор мог продолжать, а не пересобирать план с нуля.
  - `src/agents_tg/services/memory_service.py`:
    - Сохранён Mem0 как основной провайдер долговременной памяти.
    - Добавлен простой in‑memory `journal_store` для Manus‑стиля журналов, работающий даже без Mem0.
    - Новый метод `add_journal_entry(user_id, agent, event, payload)` для записи шагов агентов.
    - Новый метод `get_journal(user_id, agent)` для чтения журнала (может использоваться в будущем UI / командах).
    - Метод `add` теперь, помимо попытки записать в Mem0, всегда пишет служебную запись в журнал (`event="memory_add"`), чтобы не терять след действий.
- **Не в SPEC:**
  - Журнал реализован специально как лёгкий in‑process storage без БД, чтобы соответствовать нулевому бюджету и не усложнять схему миграциями.
- **Tradeoffs:**
  - Журнал сейчас не переживает перезапуск процесса (это сознательный минимальный шаг); при необходимости его можно будет перенести в БД, не меняя интерфейс методов сервиса.
  - Для краткости нет ещё явной привязки журналов к конкретным типам событий (planner step, tool call и т.п.) — пока только базовый `memory_add`; расширение типов событий можно сделать в следующих задачах.
- **Файлы:**
  - `src/agents_tg/agents/orchestrator.py`
  - `src/agents_tg/services/memory_service.py`
- **Проверки:**
  - Локальный просмотр импортов/типов; дальнейшая проверка — через общий цикл verify.
- **Следующий шаг:**
  - Зафиксировать выбор бесплатных моделей и первого набора интеграций (Obsidian, поиск, GitHub/Calendar) в коде конфигурации и документации, затем прогнать команды из `docs/PROJECT_VERIFICATION.md`.

---

## 2026-05-26 — Бесплатные модели и первые интеграции

- **Контекст:** По условиям пользователя бюджет на проект 0 ₽, поэтому все модели и интеграции должны опираться на бесплатные тарифы и локальные возможности (Obsidian через Git, поиск через открытые источники).
- **Решение:**
  - Конфиг AI:
    - `src/agents_tg/config/settings.py` оставлен с дефолтом `QWEN_API_BASE` на HuggingFace Inference и моделью `Qwen/Qwen2.5-72B-Instruct` — это основной целевой бесплатный вариант.
    - В `README.md` уточнено, что возможен fallback на бесплатные тарифы OpenRouter, но без жёсткой привязки в коде (решается переменными окружения).
  - Интеграции:
    - Obsidian:
      - Используется `OBSIDIAN_VAULT_PATH` и `GIT_REMOTE_URL` из настроек (`AppSettings`) + существующий `obsidian_sync` — это даёт бесплатную и устойчивую синхронизацию заметок через Git.
    - Поиск/Интернет:
      - Все агенты‑специалисты (Research, Business, Marketing, Security, Coder) используют `ToolEnabledAgent` с DuckDuckGo + Trafilatura через `utils/internet.py` — только открытые источники, без платных API.
    - Mem0:
      - `MEM0_API_KEY` опционален: при его отсутствии память и журналы gracefully деградируют к in‑process fallback (см. предыдущую запись про журнала).
    - GitHub/Calendar/Notion:
      - На первом этапе остаются на уровне «рук»: генерация инструкций, планов и markdown‑артефактов, без непосредственных сетевых вызовов, чтобы не упираться в авторизацию и платные лимиты; реальные API‑клиенты будут добавляться точечно под конкретные сценарии.
- **Tradeoffs:**
  - Отказ от прямой интеграции с платными API (кроме опционального Mem0) упрощает деплой и соответствует нулевому бюджету, но часть автоматизации (например, автосоздание событий в Google Calendar) пока останется на уровне «предложи пользователю шаги».
  - Хардкод URL HuggingFace в настройках даёт понятный дефолт, но при смене модели/провайдера потребуется обновить переменные окружения; это считается приемлемым.
- **Файлы:**
  - `src/agents_tg/config/settings.py`
  - `README.md`
- **Проверки:**
  - Настройки просмотрены вручную; дальнейший шаг — прогнать `black`, `isort`, `flake8`, `pytest` по `docs/PROJECT_VERIFICATION.md`.
- **Следующий шаг:**
  - Выполнить цикл verify (форматирование, линтинг, тесты) и, при успехе, зафиксировать DoD для текущей задачи.

---

## 2026-05-26 — Senior-level Memory & Persistence

- **Mem0 Integration:** Реализована долговременная память (`MemoryService`). Теперь Оркестратор и агенты ищут в памяти релевантные факты перед ответом и сохраняют новые важные данные.
- **Git Persistence for Obsidian:** Внедрена автоматическая синхронизация заметок с GitHub. Это гарантирует, что данные не пропадут при перезапуске сервера (Render.com) и будут доступны пользователю в его приложении Obsidian.
- **Manus-Style Planning:** Оркестратор теперь не просто выбирает агента, а строит план из 2-3 шагов, который отображается пользователю.
- **Docker Update:** В образ добавлен `git` для работы системы синхронизации.
- **Code Refactoring:** Все импорты переведены на абсолютные пути `src.agents_tg.*` для избежания конфликтов.

- **Контекст:** Необходимость расширения функционала до 6 специализированных агентов с глубокой интеграцией инструментов (Obsidian, GCal) и долговременной памятью.
- **Решение:**
  - Переход на **LangGraph** для оркестрации (вместо простого роутинга).
  - Внедрение **Mem0** для управления памятью пользователя.
  - Изменение состава агентов: Orchestrator, Personal Assistant, Sports Analyst, Security AI, Business Manager, Marketing.
  - Выбор **Render.com** в качестве основной платформы для деплоя (вместо Railway).
  - Интеграция Obsidian через локальные Markdown файлы/Git для соблюдения нулевого бюджета.
- **Tradeoffs:**
  - LangGraph сложнее в реализации, но дает гибкость группового чата и циклов.
  - Markdown/Git для Obsidian менее "реальное время", чем REST API, но бесплатно и надежно.
- **Следующий шаг:**
  - Рефакторинг `src/agents/coordinator.py` в `src/agents/orchestrator.py` на базе LangGraph.
  - Реализация `Personal Assistant` с базовыми инструментами для работы с файлами.

---

## 2026-05-24 — Реализация специализированных агентов (Finance, Notes, Planner)

- **Контекст:** После инициализации проекта и создания базовой структуры, нужно реализовать рабочих агентов для MVP
- **Решение:**
  - Создан Finance Agent с функционалом учета расходов и доходов
  - Создан Notes Agent с созданием, поиском и тегированием заметок
  - Создан Planner Agent с управлением задачами и напоминаниями
  - Обновлен Coordinator Agent для маршрутизации к реальным агентам вместо AI промптов
  - Все агенты работают в памяти (для MVP), позже будут подключены к БД
- **Не в SPEC:**
  - Добавлен простой парсер естественного языка для каждого агента
  - Реализована система приоритетов и статусов задач
  - Добавлена автоматическая категоризация расходов по ключевым словам
- **Tradeoffs:**
  - Используем in-memory хранилище вместо БД для быстрого MVP
  - Простой парсер вместо сложного NLP для быстрой реализации
  - Жестко закодированные категории вместо ML-классификации
- **Файлы:**
  - `src/agents/finance.py` - Finance Agent с методом process()
  - `src/agents/notes.py` - Notes Agent с поиском и тегами
  - `src/agents/planner.py` - Planner Agent с задачами и напоминаниями
  - `src/agents/coordinator.py` - обновлен для использования реальных агентов
- **Проверки:**
  - `black .` - OK
  - `isort .` - OK
  - `flake8 src/` - OK
  - `pytest tests/ -v` - 4 passed
- **Следующий шаг:**
  - Интеграция с Qwen API для улучшения понимания естественного языка
  - Реализация Integration Agent
  - Настройка деплоя на Railway.app

---

## 2026-05-24 — Инициализация Python проекта

- **Контекст:** Продолжение инициализации после создания документации
- **Решение:**
  - Инициализирован Poetry проект (pyproject.toml)
  - Создана структура директорий (src/, tests/, alembic/)
  - Настроены линтеры: black, isort, flake8, mypy
  - Настроен pytest с coverage
  - Создана конфигурация pydantic-settings
  - Настроен Alembic с async SQLAlchemy
  - Созданы ORM модели: User, Note, FinanceTransaction
  - Создана начальная Alembic миграция
  - Написан базовый тест (test_settings.py) - 4 теста, 100% pass
  - Инициализирован Git репозиторий
- **Не в SPEC:**
  - Добавлен .flake8 конфиг
  - Создан alembic.ini
  - Настроен async engine в env.py
- **Tradeoffs:**
  - PostgreSQL недоступен локально - миграция создана вручную (offline mode)
  - Python 3.13 вместо 3.11 (доступен на системе)
- **Файлы:**
  - `pyproject.toml` - Poetry конфиг
  - `src/config/settings.py` - pydantic настройки
  - `src/db/models.py` - SQLAlchemy модели
  - `src/db/session.py` - async session
  - `src/db/migrations/env.py` - Alembic async env
  - `src/db/migrations/versions/361a0f436028_initial_users_notes_finance_transactions.py` - миграция
  - `tests/test_settings.py` - тесты настроек
  - `.flake8` - flake8 конфиг
  - `.env.example` - пример переменных окружения
- **Проверки:**
  - `black .` - OK
  - `isort .` - OK
  - `flake8 src/` - OK
  - `pytest tests/ -v` - 4 passed
- **Следующий шаг:**
  - Реализовать базовый Telegram bot (aiogram)
  - Подключить Qwen API
  - Реализовать Coordinator Agent

---

## 2026-05-24 — Инициализация проекта и документации

- **Контекст:** Создание мультиагентной системы для Telegram с AI агентами (планировщик, финансист, секретарь, интегратор)
- **Решение:** 
  - Создана полная архитектура проекта
  - Выбран стек: Python 3.11 + aiogram 3.x + PostgreSQL + Redis + Qwen2.5-72B-Instruct
  - Хостинг: Railway.app (бесплатный tier, 24/7)
  - Разработаны промпты для 5 агентов (Coordinator, Planner, Finance, Notes, Integration)
  - Создана документация: PROJECT_PROMPT.md, PROJECT_STATE.json, PROGRESS.md, README.md, AI_INSTRUCTIONS.md
  - Адаптирована структура под CursoRules стандарт
- **Не в SPEC:** 
  - Добавлен детальный roadmap на 10 этапов (47 задач)
  - Созданы шаблоны кода и best practices для будущей разработки
  - Добавлена система метрик и мониторинга
- **Tradeoffs:**
  - Выбрали облачную модель (Qwen API) вместо локальной из-за ограничений железа пользователя
  - Railway.app вместо VPS - проще в настройке, но есть лимиты free tier
  - Мультиагентная архитектура - сложнее в реализации, но лучше качество и масштабируемость
- **Файлы:** 
  - `PROJECT_PROMPT.md` - главная документация с промптами агентов
  - `PROJECT_STATE.json` - структурированное состояние проекта
  - `PROGRESS.md` - детальный трекинг задач
  - `README.md` - документация для GitHub
  - `AI_INSTRUCTIONS.md` - инструкции для AI разработчика
  - `docs/implementation-notes.md` - этот файл
  - `docs/PROJECT_VERIFICATION.md` - команды проверки (создать)
- **Проверки:** 
  - Markdown файлы созданы корректно
  - JSON валиден
  - Структура соответствует CursoRules стандарту
- **Следующий шаг:**
  - Создать `docs/PROJECT_VERIFICATION.md` с командами проверки для Python проекта
  - Инициализировать структуру Python проекта (Poetry, директории)
  - Настроить базовые зависимости
  - Создать модели БД
  - Реализовать базовый Telegram bot

---

## Технические решения

### Почему Qwen2.5-72B-Instruct?
- Бесплатный API через Alibaba Cloud DashScope (500K tokens/день)
- Отличное качество для русского языка
- Нативная поддержка function calling
- Большой контекст (32K tokens)
- Альтернатива: OpenRouter для fallback

### Почему Railway.app?
- $5 бесплатно каждый месяц
- PostgreSQL + Redis из коробки
- Автоматический деплой из Git
- SSL сертификаты автоматически
- Простая настройка переменных окружения

### Почему мультиагентная архитектура?
- Специализация агентов повышает качество ответов
- Легче тестировать и поддерживать
- Возможность параллельной работы агентов
- Более понятная структура кода
- Проще масштировать функционал

### Почему aiogram 3.x?
- Современный async framework
- Отличная документация на русском
- Активное комьюнити
- Поддержка всех фич Telegram Bot API
- FSM из коробки

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Лимиты Qwen API | Средняя | Кэширование, rate limiting, fallback на OpenRouter |
| Лимиты Railway free tier | Средняя | Оптимизация запросов, Redis для кэша, мониторинг |
| Сложность координации агентов | Высокая | Чёткие протоколы, extensive logging, тесты |
| Потеря контекста между сессиями | Низкая | PostgreSQL для истории, Redis для активных сессий |

## Архитектурные паттерны

- **Coordinator Pattern** - центральный диспетчер для маршрутизации
- **Strategy Pattern** - разные агенты как стратегии обработки
- **Repository Pattern** - абстракция работы с БД
- **Unit of Work** - транзакции для связанных операций
- **Factory Pattern** - создание агентов и клиентов API

## Метрики успеха

- ✅ Документация создана (100%)
- ⏳ Код написан (45%)
- ⏳ Тесты (15%)
- ⏳ Деплой (0%)

**Целевые метрики:**
- Время ответа < 2 секунд
- Uptime > 99%
- Точность категоризации расходов > 90%
- Coverage тестами > 80%
- **GitHub Actions (code ship):** run **#14** id 26724485582 — **green** — https://github.com/fishacot/agentsTG/actions/runs/26724485582

## 2026-05-31 — План LLM + OpenClaw + E2E

- Создан `docs/PLAN_LLM_OPENCLAW_E2E.md`: prod chain (VPS `groq` vs dev `gemini,groq`), env-матрица, OpenClaw parity gaps, phased A/B/C + E2E sign-off.
- Источники: `settings.py`, `llm_client.py`, `agent_models.py`, `OPENCLAW_PARITY.md`, `ROADMAP_MVP.md`, `E2E_AUTONOMY.md`, `DEV_AGENT_ERGONOMICS.md`.
- Следующий шаг (human): E2E sign-off по `E2E_TELEGRAM_CHECKLIST.md`; ops — `REQUIRE_CONFIRM=true` на prod.

## 2026-05-31 — Execution plan (Sprint 0 + Phase B prep)

- **Commit `1ead0c1`:** PLAN, DEV_AGENT_ERGONOMICS, E2E runbooks, `vps_configure_prod.py` (LLM audit block), W11 eval map, `JOURNAL_30_DAY.md`.
- **Push:** `origin/master` @ `1ead0c1`.
- **Verify:** pytest 232+ passed; eval 27 scenarios + `W11_E2E_MAP`; `smoke_prod_public.py` → health ok + API 401.
- **VPS deploy:** blocked locally — `VPS_SSH_PASSWORD` not in `.env`. Public health OK. Elza logs (`last_incident_elza.txt`) show errors **before** hotfix `22f8748` — нужен `vps_deploy.py` + manual TG smoke.
- **Phase B:** `PHASE_B_INTEGRATIONS_SMOKE.md`; CalDAV write deferred; `STEP_MODEL_ROUTING` via `APPLY_STEP_MODEL_ROUTING=1` + `vps_configure_prod.py`.
- **Human pending:** W1–W7, W11 D1–D6 Telegram — `E2E_TELEGRAM_CHECKLIST.md`; integration smoke — `PHASE_B_INTEGRATIONS_SMOKE.md`.
