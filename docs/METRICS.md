# Metrics spec (solo owner)

Lightweight observability for «лучше Manus в нише Telegram». No PII in exports.

## Definitions

| Metric | Definition | Source tables |
|--------|------------|---------------|
| **task_success_rate** | `done` tasks / (`done` + `failed` + `cancelled`) in window | `agent_tasks` |
| **replan_rate** | Steps or tasks with replan signal / total plan runs | `plan_steps`, `agent_tasks.context_json` |
| **confirm_rate** | Confirmations created / gated tool calls (proxy) | `pending_confirmations` |
| **verify_fail_rate** | Failed verify / steps with verify | JOURNAL + `plan_steps` |

## SQL sketches (PostgreSQL)

### Task success (7d)

```sql
SELECT
  COUNT(*) FILTER (WHERE status = 'done')::float
  / NULLIF(COUNT(*) FILTER (WHERE status IN ('done','failed','cancelled')), 0) AS task_success_rate
FROM agent_tasks
WHERE created_at >= NOW() - INTERVAL '7 days';
```

### Replan proxy (context contains replan)

```sql
SELECT
  COUNT(*) FILTER (
    WHERE context_json::text ILIKE '%replan%'
       OR context_json::text ILIKE '%[[REPLAN]]%'
  )::float
  / NULLIF(COUNT(*), 0) AS replan_rate
FROM agent_tasks
WHERE created_at >= NOW() - INTERVAL '7 days'
  AND status IN ('done', 'failed', 'running');
```

### Confirmation rate (7d)

```sql
SELECT
  COUNT(*)::float / NULLIF(
    (SELECT COUNT(*) FROM agent_jobs WHERE trigger = 'inbound' AND created_at >= NOW() - INTERVAL '7 days'),
    0
  ) AS confirm_rate
FROM pending_confirmations
WHERE created_at >= NOW() - INTERVAL '7 days';
```

### Recipe reuse

```sql
SELECT intent_sample, success_count, jsonb_array_length(steps_json::jsonb) AS step_count
FROM plan_recipes
WHERE user_id = :owner_id
ORDER BY success_count DESC
LIMIT 10;
```

## Targets (solo MVP)

| Metric | Target (initial) |
|--------|------------------|
| task_success_rate | ≥ 0.85 on orchestrator plans |
| replan_rate | ≤ 0.25 |
| confirm_rate | ≤ 0.15 (avoid fatigue) |
| verify_fail_rate | trending down week-over-week |

## Reporting

- Weekly: run SQL in Neon console or `scripts/` (future).
- Log lines: `structured_log` events `plan_done`, `verify_fail`, `confirm_pending`.
- See [`EVAL_HARNESS.md`](EVAL_HARNESS.md) for regression scenarios.
