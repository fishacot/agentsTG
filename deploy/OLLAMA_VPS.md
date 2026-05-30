# Ollama on VPS (optional, after RAM upgrade)

Self-hosted LLM on the same VPS is **not recommended** on the current FirstByte plan (~1GB RAM, ~9GB disk). A 7B model needs roughly **8GB RAM** and **5GB disk**.

## When to use

- VPS upgraded to **8GB+ RAM** and **15GB+ disk**
- You want zero external API dependency for simple replies

## Setup (after upgrade)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b   # or phi3.5:mini for CPU
```

Add to `.env`:

```env
LLM_PROVIDER_CHAIN=ollama,gemini,groq
OLLAMA_API_BASE=http://127.0.0.1:11434/v1
```

Wire `ollama` provider in `llm_client.py` when enabled (future phase).

## Recommended for now

Use **Gemini Flash** (free, high TPM) + **Groq** fallback — see `deploy/TIMWEB_VPS_GUIDE.md`.
