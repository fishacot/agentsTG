# FirstByte VPS — production deploy

Production server: **91.186.221.32** (FirstByte FI), path `/opt/agentsTG`, systemd `agents-tg`.

## Prerequisites

- SSH access (root or `botsuser`)
- All 7 `BOT_TOKEN_*` in `.env`
- **Gemini API key** (free): https://aistudio.google.com/apikey
- Groq API key as fallback

## Required `.env` (LLM)

```env
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...
LLM_PROVIDER_CHAIN=gemini,groq
```

Without `GEMINI_API_KEY` the bot falls back to Groq only and may hit **429 TPM** on long prompts.

## Update after git push

```bash
cd /opt/agentsTG
git pull
sudo systemctl restart agents-tg
sudo journalctl -u agents-tg -n 30
```

## Telegram acceptance

1. **Эльза** — «расскажи что ты можешь» → instant HTML, no error
2. **Егор** — «привет» → reply from Egor only, no plan, no Elza voice
3. **Руслан** — «hello world на Python» → code snippet
4. Three messages in a row — no «перегрузка AI»

## Logs

```bash
sudo journalctl -u agents-tg -f
grep -i "429\|rate\|gemini\|groq"  # check provider usage
```

## RAM note

~1GB RAM — **no Ollama**. See [`OLLAMA_VPS.md`](OLLAMA_VPS.md) after RAM upgrade.
