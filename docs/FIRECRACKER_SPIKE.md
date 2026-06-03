# Firecracker sandbox spike — go/no-go

**Date:** 2026-06-03  
**Verdict:** **NO-GO** for MVP critical path (keep `SANDBOX_MODE=subprocess|docker`).

## Goal

Evaluate Firecracker microVMs vs current `sandbox/docker_runner.py` for `run_code` tier FULL.

## Criteria

| Criterion | Firecracker | Current docker/subprocess |
|-----------|-------------|---------------------------|
| VPS ~1GB RAM | Poor fit (host overhead) | OK |
| Cold start | Seconds | Sub-second subprocess |
| Ops complexity | KVM, kernel, images | Already wired |
| OpenClaw parity | P2 deferred in parity doc | **done** |

## Spike tasks (if revisited)

1. Branch `spike/firecracker` — hello-world VM boot on staging only.
2. Measure boot time + memory on 2GB VPS.
3. Wire optional `SANDBOX_MODE=firecracker` behind flag.

## Go/no-go

| Decision | Rationale |
|----------|-----------|
| **NO-GO (MVP)** | Solo VPS constraints; subprocess/docker sufficient for owner trust tier |
| **Revisit** | Multi-tenant or untrusted code from third parties |

## References

- [`docs/research/03-execution.md`](research/03-execution.md)
- [`OPENCLAW_PARITY.md`](OPENCLAW_PARITY.md) — sandbox row
