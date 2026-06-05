# Что такое E2E (для agentsTG)

**E2E (end-to-end)** — проверка **цепочки целиком**, как у реального пользователя, а не отдельных функций в pytest.

| Уровень | Что проверяет | Пример |
|---------|----------------|--------|
| **Unit** | Одна функция/модуль | `resolve_step_model("finalize")` |
| **Integration** | Несколько модулей без Telegram | `plan_executor` + mock dispatch |
| **E2E** | Бот + БД + VPS + вы в Telegram | «Егор, план из 3 шагов» → прогресс → финал |

## Зачем это в roadmap

Критерий **MVP done** в [`ROADMAP_MVP.md`](ROADMAP_MVP.md) требует не только зелёных тестов, но и **подписанного** [`E2E_SIGNOFF_TEMPLATE.md`](E2E_SIGNOFF_TEMPLATE.md): сценарии из [`E2E_AUTONOMY.md`](E2E_AUTONOMY.md) (W1–W11) с датой Pass.

## Что можно автоматизировать на VPS

Без ваших сообщений в Telegram:

- `curl :8080/` — health + Neon (`database.status`)
- `REQUIRE_CONFIRM=true` в `.env` на сервере
- `POST /v1/agent/run` без токена → **401**
- `POST /v1/agent/run` с `AGENT_RUN_API_TOKEN` → **200**
- `systemctl is-active agents-tg` → **active**

Лог: [`last_vps_e2e_automated.txt`](last_vps_e2e_automated.txt). Скрипт: `scripts/vps_configure_prod.py`.

## Что только вручную в Telegram

- Привет, план 2+ шагов, cancel, confirm Да/Нет (D6)
- Напоминание через 3 минуты
- Deep research ack
- Групповой чат

Чеклист на ~10 минут: [`E2E_TELEGRAM_CHECKLIST.md`](E2E_TELEGRAM_CHECKLIST.md).
