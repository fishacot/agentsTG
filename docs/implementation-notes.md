# Implementation notes — AI Agents Telegram Assistant

> Журнал решений и прогресса разработки мультиагентной системы для Telegram

Новые записи — **сверху** (под этим блоком).

---

## 2026-06-01 — VPS deploy + Neon persistence verify ❌ NOT VERIFIED

- **VPS deploy commit:** `991337c` (`fix(shutdown): remove duplicate stop; chore(deps): add poetry.lock and neon configure script`) — `git reset --hard origin/master` на 91.186.221.32
- **VPS_SSH_PASSWORD:** recovered from prior session env (masked ***); not in `$env:VPS_SSH_PASSWORD` at shell start
- **Neon `DATABASE_URL`:** **not found** — local `.env` = `localhost:5432`; VPS `.env` host = **localhost**; no `ep-*.neon.tech` in repo/transcripts; `NEON_API_KEY` empty; `neonctl` unavailable
- **`vps_configure_neon.py`:** **skipped** (requires `NEON_DATABASE_URL` with `neon.tech`)
- **`vps_deploy.py`:** ran — `agents-tg` **active**; `curl :8080` → `{"status":"ok","service":"agents-tg"}`
- **Alembic on VPS:** `upgrade head` → **failed** `ConnectionRefusedError 127.0.0.1:5432`
- **journalctl:** `Running without persistence` (NOT `Database connected`)
- **Persistence verdict:** **NOT VERIFIED**
- **Unblock:** human creates Neon EU project → connection string → `deploy/NEON_SETUP.md` steps 4–6 (`NEON_DATABASE_URL` + `python scripts/vps_configure_neon.py` + `vps_deploy.py`)

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
