# Integrations — Phase 2 MVP

Anchor APIs for solo-owner «штаб» in Telegram. Code: `src/agents_tg/services/integrations/`, tools: `services/tools/integration_tools.py`.

## Environment variables

| Variable | Required | Used by | Notes |
|----------|----------|---------|-------|
| `CALDAV_URL` | No | Эльза (PA) | CalDAV endpoint; without it calendar returns structured **stub** |
| `GITHUB_TOKEN` | No | Руслан (coder) | Personal access token with `repo` or `public_repo` + read issues |
| `APP_TIMEZONE` | No | Calendar | Default `Europe/Moscow` for event times |
| `MCP_ENABLED` | No | Егор (orchestrator only) | Default `false`; set `true` only for POC |
| `MCP_SERVERS` | No | MCP bridge | JSON list, e.g. `[{"name":"fs","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/path"]}]` |

**Never commit** tokens or `.env` to the repo. Rotate if exposed in chat.

## Scopes and permissions

### Calendar (CalDAV)

- **MVP:** stub when `CALDAV_URL` unset; audit entry in workspace JOURNAL.
- **With URL:** intent logged; full CalDAV write deferred to next wave.
- **Rate limit:** 20 calls / 60s per user per integration (in-process).

### GitHub

- **Token scopes:** `read:org` not required for public repos; private repos need `repo` scope.
- **API:** `GET /repos/{owner}/{name}/issues` — open issues only (PRs filtered out).
- **Without token:** tool returns `ok: false` + hint (no exception).

### Research citations (Ульяна)

- **No extra env** — uses DuckDuckGo + page fetch (`search_provider.py`).
- `deep_research` returns `citations` + `citation_block` (Telegram HTML links).
- Tier FULL + `include_web_tools` required for `deep_research` tool.

### Staff summary (Егор)

- Reads `agent_tasks` (PG) + in-memory plan fallback.
- Tool: `staff_summary` on orchestrator.

## Agent → tool mapping

| Agent key | Tools |
|-----------|-------|
| `personal_assistant` | `calendar_create_event` |
| `coder` | `github_list_issues` |
| `orchestrator` | `staff_summary` (+ delegation tools) |
| `research` | `deep_research` (builtin, web tier) |

## MCP POC

- **Default:** `MCP_ENABLED=false` — no MCP tools in agent loop.
- **When enabled:** orchestrator gets `mcp_echo`; client allowlist: `echo`, `ping`, `read_file`, `list_directory`.
- Real stdio servers configured via `MCP_SERVERS`; unlisted tools rejected.

## Limits

| Limit | Value |
|-------|-------|
| Integration rate limit | 20 req / 60s / user / integration |
| GitHub issues per call | max 30 (`per_page`) |
| Research citations in block | 5 (default `max_items`) |
| Calendar title | 200 chars |

## Telegram smoke scenarios

Run against prod/staging per [`deploy/FIRSTBYTE_VPS.md`](../deploy/FIRSTBYTE_VPS.md). Record results in `docs/implementation-notes.md` (no secrets).

### 1. Calendar stub (Эльза / PA)

1. DM PA: «Создай встречу завтра 15:00 — созвон с командой».
2. **Expect:** confirmation of event with ISO time; note about `CALDAV_URL` if unset.
3. **Journal:** `integration/calendar` entry in workspace JOURNAL.

### 2. GitHub issues (Руслан / coder)

1. Without `GITHUB_TOKEN`: «Покажи issues в owner/repo».
2. **Expect:** polite error + hint to set token.
3. With token + real repo: numbered list with titles and links.

### 3. Research with citations (Ульяна / research)

1. Ask a factual question needing web (FULL tier).
2. **Expect:** answer with **Находки** section; numbered `<a href="...">` links from `citation_block`.

### 4. Staff summary (Егор / orchestrator)

1. Create a multi-step plan, then ask: «Что сейчас в работе?»
2. **Expect:** `staff_summary` lists active tasks or empty state with hint.

### 5. MCP (optional)

1. Set `MCP_ENABLED=true`, `MCP_SERVERS=[{"name":"default","command":"..."}]`.
2. Orchestrator: use `mcp_echo` with a test message.
3. **Expect:** echo result or allowlist error for unknown tool.

## Verify (local)

```bash
python -m pytest tests/test_integrations.py tests/test_search_provider.py -v --tb=short
```

Full suite: [`PROJECT_VERIFICATION.md`](PROJECT_VERIFICATION.md).
