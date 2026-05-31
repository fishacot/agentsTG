# Neon Postgres — настройка для agentsTG

## Зачем

Neon — бесплатная облачная PostgreSQL. Нужна для:

- напоминаний (`reminders`) — переживают рестарт VPS;
- истории чата и фактов пользователя.

## Шаги

1. Откройте [https://neon.tech](https://neon.tech) → Sign up (GitHub/Google).
2. **New Project** → регион ближе к VPS (EU).
3. Скопируйте **Connection string** (формат `postgresql://user:pass@host/db?sslmode=require`).
4. На VPS в `/opt/agentsTG/.env` (приложение нормализует `postgresql://` → `postgresql+asyncpg://`):

```bash
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
APP_TIMEZONE=Europe/Moscow
```

**С Windows (после `git push`):** не коммитить URL в git.

```powershell
$env:VPS_SSH_PASSWORD = '...'   # root@91.186.221.32
$env:NEON_DATABASE_URL = 'postgresql+asyncpg://...@....neon.tech/...?sslmode=require'
python scripts/vps_configure_neon.py
python scripts/vps_deploy.py
```

5. Перезапуск:

```bash
cd /opt/agentsTG && git pull && systemctl restart agents-tg
```

6. Таблицы создаются автоматически при старте (`init_db`).

   Опционально вручную: `alembic upgrade head` (миграция `b2c4e8f1a903` — reminders, chat_messages, user_facts).

## Проверка

```bash
curl http://127.0.0.1:8080/  # {"status":"ok"}
journalctl -u agents-tg -f   # "Database connected"
```

## Upstash Redis (опционально, W1.10)

1. [https://upstash.com](https://upstash.com) → Redis database.
2. `REDIS_URL=rediss://...` в `.env`.
