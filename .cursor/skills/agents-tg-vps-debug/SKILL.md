# agentsTG VPS / Elza debug

## When to use

Use this skill when Telegram bots on the FirstByte VPS misbehave (silent replies, health failures, deploy issues, Elza DM bugs). Do not paste secrets into chat or commits.

## VPS context

- Host: **91.186.221.32** (FirstByte FI)
- App path: `/opt/agentsTG`
- systemd unit: `agents-tg`
- Health: `http://127.0.0.1:8080/` → `{"status":"ok", ...}`

Canonical runbook: [`deploy/FIRSTBYTE_VPS.md`](../../../deploy/FIRSTBYTE_VPS.md)

## Quick checks (SSH on VPS)

```bash
systemctl is-active agents-tg
sudo journalctl -u agents-tg -n 80 --no-pager
curl -s http://127.0.0.1:8080/
grep -E '429|rate|error|UnboundLocal' <(journalctl -u agents-tg -n 200 --no-pager)
```

Structured events: logger `agents_tg.events` (JSON lines).

## From local Windows (no secrets in repo)

Set `VPS_SSH_PASSWORD` in the shell only (never commit):

```powershell
$env:VPS_SSH_PASSWORD = '...'
python scripts/_fetch_vps_logs.py    # writes docs/last_incident_elza.txt
python scripts/vps_deploy.py         # pull + restart; log docs/last_vps_deploy.txt
python scripts/vps_configure_prod.py # prod env sanity (E2E automated)
```

## Common Elza / inbound issues

1. **No "🤖 Думаю…" / silent DM** — check dedupe in `inbound.py` / `inbound_turn.py`; see latest entry in `docs/implementation-notes.md`.
2. **Generic "Произошла ошибка"** — journalctl stack trace; recent fixes in `agent_runtime`, `reminder_service`.
3. **LLM 429 / budget** — `LLM_COOLDOWN_SEC`, `GROQ_DEFER_HEAVY_ON_BUDGET`; see `docs/RESOURCE_AND_LLM.md`.

## Deploy flow

1. Local verify: `pytest tests/ -q`
2. `git push origin master`
3. `python scripts/vps_deploy.py` with `VPS_SSH_PASSWORD`
4. Confirm: `systemctl is-active agents-tg`, health curl, spot-check Elza in Telegram

## What not to do

- Do not commit `.env`, tokens, or SSH passwords
- Do not install Ollama/AirLLM on current ~1GB RAM VPS (see `docs/DEV_AGENT_ERGONOMICS.md`)
- Do not force-push `master`
