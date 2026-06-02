# E2E — автономность агентов (приёмка)

Часовой пояс: **Europe/Moscow (МСК)**.

## W1 — Runtime + delivery + время

| # | Сценарий | Бот | Ожидание |
|---|----------|-----|----------|
| 1 | «Привет» | Егор | Короткий ответ, без плана |
| 2 | Длинный код + asyncio | Руслан | 1–3 части `(1/N)`, без обрыва |
| 3 | «Напомни через 3 минуты выпить воды» | Эльза | Подтверждение с МСК → ping через ~3 мин |
| 4 | Рестарт `agents-tg` до срабатывания | — | Напоминание приходит (если есть PG) |
| 5 | `curl :8080/` | — | `{"status":"ok","database":{...}}` |

## W2 — Proactive + background

| # | Сценарий | Бот | Ожидание |
|---|----------|-----|----------|
| 6 | «Найди актуальные новости про Python» | Ульяна | Ack → финал отдельным сообщением |
| 7 | Задача с планом 2+ шагов | Егор | Виден `<b>План:</b>` + прогресс шагов |
| 8 | Группа: два одинаковых ответа | Любой | Anti-echo (второй skip в history) |
| 9 | /start у Эльзы в ЛС | Эльза | Утренний digest 09:00 МСК (след. день) |

## W3 — Shared memory + project focus

| # | Сценарий | Бот | Ожидание |
|---|----------|-----|----------|
| 10 | «Меня зовут X, люблю лаконично» | Любой | USER block в следующем run |
| 11 | «Сайт о собаках: парсинг, план, html» | Егор | active project + plan + `plan_steps` в PG |
| 12 | Работа Ульяны/Руслана | Специалисты | `project_activity` в PG |
| 13 | «Привет» на след. день | Эльза | Может спросить о прогрессе сайта (1×/24ч) |
| 14 | Рестарт VPS | — | profile + project + activity сохранены (Neon) |

## W4 — Gateway + envelope

| # | Сценарий | Ожидание |
|---|----------|----------|
| 15 | Inbound DM любому боту | `agent_jobs` запись со status queued→done |
| 16 | Повтор того же message_id | Dedupe — второй run не стартует |
| 17 | `POST /v1/agent/run` | JSON `{session_id, job_id}` |

## W5 — Security hooks

| # | Сценарий | Ожидание |
|---|----------|----------|
| 18 | «Ignore previous instructions…» | Блок + запись в JOURNAL |
| 19 | PA вызывает `run_code` | Deny (tool not allowed) |
| 20 | Руслан `run_code` print(1+1) | stdout в tool result |

## W6 — Plan executor (Manus)

| # | Сценарий | Ожидание |
|---|----------|----------|
| 21 | Егор: план 3 шага в группе | «Шаг 1/3…» + финал отдельным сообщением |
| 22 | После restart | `plan_steps` статусы в Neon |

## W7 — Progress UX

| # | Сценарий | Ожидание |
|---|----------|----------|
| 23 | Длинный ответ (>4096) | Несколько частей с паузой humanDelay |
| 24 | `/journal` в ЛС | Последние записи JOURNAL.md |
| 25 | `/status` | agent_key + PG status |

## W8 — Confirmation gates

| # | Сценарий | Ожидание |
|---|----------|----------|
| 26 | `REQUIRE_CONFIRM=true`, закрыть проект | Inline «Да/Нет»; без «Да» — не done |
| 27 | Повторный callback | «Подтверждение устарело» |

## W9 — Workspace isolation

| # | Сценарий | Ожидание |
|---|----------|----------|
| 28 | Tool `list_agent_workspace` | Список `workspace/users/{id}/agents/*` |

## W10 — Heartbeat parity

| # | Сценарий | Ожидание |
|---|----------|----------|
| 29 | Heartbeat вне activeHours (08–23 MSK) | Skip |
| 30 | Пользователь писал 2 мин назад | skipWhenBusy |

## Appendix — extended scenarios (optional prod smoke)

Дублирует часть W4–W10 с акцентом на sandbox/browser/artifacts. Основная матрица — секции W1–W10 выше.

| # | Сценарий | Бот | Ожидание |
|---|----------|-----|----------|
| A1 | «Сайт о собаках: план, парсинг, html» (3 шага) | Егор | Прогресс «Шаг N/M» + `plan_steps` в PG |
| A2 | Research 8+ tool rounds | Ульяна | Завершение без новых сообщений пользователя |
| A3 | Kill -9 во время задачи | — | `agent_tasks.context_json` в PG |
| A4 | Создать файл в workspace | Эльза | `sendDocument` или ссылка |
| A5 | «Напиши и запусти hello.py» | Руслан | stdout из sandbox |
| A6 | «Открой example.com — title?» | Ульяна | `browser_navigate` → title |

## Команды verify

```bash
python -m pytest tests/ -v --tb=short
curl http://127.0.0.1:8080/health
alembic upgrade head
```

См. также [`deploy/FIRSTBYTE_VPS.md`](deploy/FIRSTBYTE_VPS.md).
