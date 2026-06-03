# FirstByte VPS — production deploy

Production server: **91.186.221.32** (FirstByte FI), path `/opt/agentsTG`, systemd `agents-tg`.

## Prerequisites

- SSH access (root or `botsuser`)
- All 7 `BOT_TOKEN_*` in `.env`
- Groq API key (VPS: `LLM_PROVIDER_CHAIN=groq`)
- Optional: Neon `DATABASE_URL` (reminders survive restart) — [`NEON_SETUP.md`](NEON_SETUP.md)
- Optional: Upstash `REDIS_URL` (dedupe, run locks)

## Required `.env` (runtime)

```env
GROQ_API_KEY=gsk_...
LLM_PROVIDER_CHAIN=groq
APP_TIMEZONE=Europe/Moscow
HEALTH_PORT=8080
MESSAGE_DEBOUNCE_MS=2000
LLM_COOLDOWN_SEC=4.0
LLM_SOFT_DAILY_CALLS=80
MAX_PLAN_STEPS=4
GROQ_DEFER_HEAVY_ON_BUDGET=true
NOTEBOOK_MAX_CHARS=1500
```

См. [`docs/RESOURCE_AND_LLM.md`](../docs/RESOURCE_AND_LLM.md) — память вне Groq (NOTEBOOK.md), лимиты планов и мягкий дневной бюджет.

## Update after git push

```bash
cd /opt/agentsTG
git pull
# optional: alembic upgrade head
sudo systemctl restart agents-tg
sudo journalctl -u agents-tg -n 30
curl -s http://127.0.0.1:8080/
```

**С локальной машины (Windows):** после `git push origin master`:

```powershell
$env:VPS_SSH_PASSWORD='...'   # не коммитить
python scripts/vps_deploy.py
```

**Neon Postgres (persistence):** [`NEON_SETUP.md`](NEON_SETUP.md) — `NEON_DATABASE_URL` + `python scripts/vps_configure_neon.py`, затем `vps_deploy.py`.

## Telegram acceptance (agent autonomy)

See [`docs/E2E_AUTONOMY.md`](../docs/E2E_AUTONOMY.md).

1. **Эльза** — «напомни через 3 минуты …» → подтверждение с МСК → ping
2. **Руслан** — длинный код → 2–3 части `(1/N)`
3. **Ульяна** — «найди …» → ack + финал отдельным сообщением
4. **Егор** — план 2+ шагов → виден план + async итог
5. **Health** — `curl :8080/` → `{"status":"ok"}`

## Logs

```bash
sudo journalctl -u agents-tg -f
grep -E 'agents_tg.events|429|rate' 
```

Structured events: logger `agents_tg.events` (JSON lines).

## RAM note

~1GB RAM — **no Ollama**. See [`OLLAMA_VPS.md`](OLLAMA_VPS.md) after RAM upgrade.
