# Resource guardrails (VPS 1GB, Groq, env)

Living doc for **solo owner** MVP. No secrets in this file — configure via `.env` on VPS.

## VPS (~1 GB RAM)

- Run **one** `agents-tg` process; avoid Ollama / local LLM on the same host.
- Docker sandbox (`SANDBOX_MODE=docker`) is opt-in; default `subprocess` is lighter.
- Workspace files (`workspace/users/{id}/NOTEPAD.md`, `MEMORY.md`, `JOURNAL.md`) are the cheap external memory layer — prefer tools + `PREFER_FILE_MEMORY=true` over huge chat history.

## Groq / provider limits

| Mechanism | Env | Default | Effect |
|-----------|-----|---------|--------|
| Per-request cooldown | `LLM_COOLDOWN_SEC` | 3.0 | Min gap between LLM calls per user |
| Daily soft cap | `LLM_DAILY_SOFT_CAP` | 0 (off) | Max LLM turns per user per UTC day |
| Full-tier token cap | `MAX_TOKENS_FULL_TIER` | 900 | Upper bound for FULL prompt tier |
| Plan step cap | `PLAN_MAX_STEPS` | 4 | Multi-step plans trimmed before execution |
| Confirm gates | `REQUIRE_CONFIRM` | false | When true: `update_project_status:done`, `run_code` need inline confirm |

Implementation: `llm_cooldown.py`, `llm_usage_guard.py`, `llm_budget.py`, `agent_runtime.py`, `orchestrator_delegate.py`.

## File memory (NOTEPAD)

| Env | Default | Effect |
|-----|---------|--------|
| `PREFER_FILE_MEMORY` | true | Inject `MEMORY.md` + `NOTEPAD.md` into system prompt |
| `NOTEPAD_MAX_CHARS` | 1500 | Max NOTEPAD excerpt in prompt |

Tools: `owner_notepad_read`, `owner_notepad_append` (PA + orchestrator via `shared_context_tools.py`).

## Operational checks

- Health: `curl http://127.0.0.1:8080/` → database ok
- Verify: `python -m pytest tests/ -v --tb=short`
- Prod E2E: [`E2E_AUTONOMY.md`](E2E_AUTONOMY.md), sign-off template [`E2E_SIGNOFF_TEMPLATE.md`](E2E_SIGNOFF_TEMPLATE.md)

## When limits hit

- **Cooldown / daily cap:** user sees a short wait message; no silent failure.
- **Plan trim:** user sees «План сокращён до лимита VPS…» — send follow-up for extra steps.
- **Groq 429:** rate-limit reply from `agent_runner` / thinking message edit.
