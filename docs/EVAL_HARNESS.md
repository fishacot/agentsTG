# Eval harness (phase 5)

Regression suite for Manus-like behavior **without** live Telegram in CI.

## Scope

| Layer | Tool | Count |
|-------|------|-------|
| Unit / contract | `pytest tests/test_eval_scenarios.py` | 5–10 fixtures |
| Integration | existing `tests/test_*` | verify, delegation, confirm |
| Prod E2E | [`E2E_AUTONOMY.md`](E2E_AUTONOMY.md) W1–W11 | manual sign-off |

## Scenario fixtures

Each fixture in `tests/test_eval_scenarios.py` defines:

- `id` — stable name (`plan_two_step`, `confirm_gate`, …)
- `inputs` — user text, tier, tools stub
- `expect` — substring, status, or callable assertion

Run:

```bash
python -m pytest tests/test_eval_scenarios.py -v --tb=short
```

Full suite:

```bash
python -m pytest tests/ -v --tb=short
```

## Roadmap to 20–30 scenarios

1. Map E2E W11 D1–D10 to pytest fixtures (no bot token).
2. Add golden-file snapshots for `verify_step` outcomes.
3. Optional: nightly job with recorded LLM responses (vcr.py) — **not** in critical path.

## Acceptance

- All eval scenario tests green in CI.
- New behavior → new fixture before merge (team-kit `verify-this`).
