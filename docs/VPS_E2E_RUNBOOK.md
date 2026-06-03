# VPS E2E runbook (один вечер)

Цель: закрыть **фазу 0** по [`ROADMAP_MVP.md`](ROADMAP_MVP.md) — подписать [`E2E_SIGNOFF_TEMPLATE.md`](E2E_SIGNOFF_TEMPLATE.md).

## 1. Env (prod)

```bash
# на VPS в .env
REQUIRE_CONFIRM=true
AGENT_RUN_API_TOKEN=<случайный_секрет>
DATABASE_URL=<neon>
DEBUG=false
```

Деплой: [`deploy/FIRSTBYTE_VPS.md`](../deploy/FIRSTBYTE_VPS.md).

```bash
alembic upgrade head
curl -s http://127.0.0.1:8080/ | jq .database
```

Ожидание: `"status": "ok"`.

## 2. Минимальный прогон Telegram

| ID | Действие | Pass |
|----|----------|------|
| W1 | `/start` у оркестратора, ответ без 500 | |
| W6 | Запрос с планом 2+ шага; один статус edit + cancel | |
| D6 | `REQUIRE_CONFIRM=true`, `run_code` или закрыть проект → Да → replay | |

Подробности: [`E2E_AUTONOMY.md`](E2E_AUTONOMY.md).

## 3. HTTP smoke

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8080/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"agent_key":"personal_assistant","user_id":0,"text":"ping"}'
# без токена → 401/403 (не 200)
```

С токеном:

```bash
curl -s -X POST http://127.0.0.1:8080/v1/agent/run \
  -H "Authorization: Bearer <AGENT_RUN_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"agent_key":"personal_assistant","user_id":<YOUR_TG_ID>,"chat_id":<YOUR_TG_ID>,"text":"ping"}'
```

## 4. Записать результат

Скопировать даты в `E2E_SIGNOFF_TEMPLATE.md` и строку в `docs/implementation-notes.md`.

## Что уже в коде (не требует VPS)

- `STEP_MODEL_ROUTING` в `llm_client`
- `task_id` в plan dispatch + PG migration `g1h3i5j7k019`
- Confirm inline в фоновых планах
- Прогресс плана: одно сообщение (`plan_progress.py`)
- A2A: `on_a2a_step_callback` + resume при активном плане
