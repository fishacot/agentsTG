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
LLM_COOLDOWN_SEC=3.0
```

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
