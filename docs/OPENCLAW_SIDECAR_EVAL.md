# OpenClaw Node sidecar — evaluation gate

> Phase 13 deliverable. **No Node sidecar code in agentsTG** — decision document only.

## Context

OpenClaw upstream runs a **Node.js Gateway daemon** with WebSocket JSON API, plugin lifecycle, and SQLite Task Brain. agentsTG implements **Python-first L1–L4 parity** in-process (`gateway/`, `agent_jobs` PG, hooks, PlanExecutor).

## Options

| Option | Pros | Cons | Cost |
|--------|------|------|------|
| **A — Stay Python** (current) | Single stack, 7-bot model preserved, Neon PG | No 1:1 WS protocol; plugin ecosystem separate | Free |
| **B — Hybrid sidecar** | Max upstream parity; reuse OpenClaw plugins | Two runtimes, bridge auth, deploy complexity | Medium |
| **C — Full migration to OpenClaw CLI** | Highest fidelity | Rewrite channel layer; lose aiogram specifics | High |

## Recommendation (2026-06-01)

**Stay on Option A** until one of these triggers:

1. Need **official OpenClaw plugins** (npm) without Python ports.
2. Need **WS/OpenAI-compatible API** for external clients at scale.
3. Team capacity for **dual-runtime ops** (Node + Python on VPS).

## Migration path if triggered (Option B sketch)

1. Run OpenClaw gateway on `:18789` (WS).
2. Bridge `TelegramAdapter` → WS `connect` + `agent.run` instead of in-process `gateway_router`.
3. Map `agent_jobs` PG ↔ OpenClaw SQLite via sync job (hourly) or replace with PG-only.
4. Keep **7 Telegram bots** as thin L1 clients; LLM/tools remain Python or move per plugin.

## Decision gate checklist

- [ ] Product requires upstream plugin X (name/version)
- [ ] External API consumers need OpenClaw WS schema
- [ ] Python plugin registry insufficient after 2 quarters
- [ ] Ops budget for second process + monitoring

**Status:** Option A — **accepted**. Re-evaluate Q4 2026 or on explicit product request.

## References

- [OPENCLAW_PARITY.md](OPENCLAW_PARITY.md)
- [openclaw architecture](https://github.com/openclaw/openclaw/blob/main/docs/concepts/architecture.md)
- In-repo: `src/agents_tg/gateway/`, `src/agents_tg/mcp/client.py` (stub bridge point)
