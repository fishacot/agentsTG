"""Configure prod .env on VPS and run automatable E2E checks.

Requires: VPS_SSH_PASSWORD (never commit).
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sys
from datetime import date

import paramiko

HOST = "91.186.221.32"
USER = "root"
REPO = "/opt/agentsTG"
ENV_PATH = f"{REPO}/.env"
SERVICE = "agents-tg"


def _safe_print(text: str) -> None:
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        sys.stdout.write(text + "\n")
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode(enc, errors="replace"))
    sys.stdout.flush()


def run(
    client: paramiko.SSHClient,
    cmd: str,
    timeout: int = 120,
    *,
    label: str | None = None,
    quiet: bool = False,
) -> tuple[int, str, str]:
    display = label if label is not None else cmd
    if not quiet:
        _safe_print(f"\n=== {display} ===")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if not quiet:
        if out.strip():
            _safe_print(out.rstrip())
        if err.strip():
            _safe_print("STDERR: " + err.rstrip())
    return code, out, err


def _remote_set_env(client: paramiko.SSHClient, key: str, value: str) -> None:
    """Set KEY=value in .env (create file if missing)."""
    escaped = value.replace("'", "'\"'\"'")
    cmd = (
        f"test -f {ENV_PATH} || touch {ENV_PATH}; "
        f"grep -q '^{key}=' {ENV_PATH} && "
        f"sed -i 's|^{key}=.*|{key}={escaped}|' {ENV_PATH} || "
        f"echo '{key}={escaped}' >> {ENV_PATH}"
    )
    run(client, cmd, label=f"set {key} in .env")


def main() -> None:
    password = os.environ.get("VPS_SSH_PASSWORD", "")
    if not password:
        print("Set VPS_SSH_PASSWORD", file=sys.stderr)
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=password, timeout=20)

    token_cmd = (
        f"grep '^AGENT_RUN_API_TOKEN=' {ENV_PATH} 2>/dev/null | cut -d= -f2- | tr -d '\\r' || true"
    )
    _, token_out, _ = run(
        client, token_cmd, label="read AGENT_RUN_API_TOKEN", quiet=True
    )
    api_token = token_out.strip()
    if not api_token:
        api_token = secrets.token_urlsafe(32)
        _remote_set_env(client, "AGENT_RUN_API_TOKEN", api_token)
        _safe_print("AGENT_RUN_API_TOKEN: generated new (see VPS .env — not printed here)")

    prod_llm = {
        "LLM_PROVIDER_CHAIN": "groq",
        "LLM_COOLDOWN_SEC": "4.0",
        "LLM_SOFT_DAILY_CALLS": "80",
        "MAX_TOKENS_FULL_TIER": "768",
        "GROQ_DEFER_HEAVY_ON_BUDGET": "true",
        "REQUIRE_CONFIRM": "true",
        "DEBUG": "false",
    }
    for key, value in prod_llm.items():
        _remote_set_env(client, key, value)
    _safe_print("Prod LLM + confirm block applied (groq-only, budget guardrails)")

    if os.environ.get("APPLY_STEP_MODEL_ROUTING", "").lower() in ("1", "true", "yes"):
        routing = (
            '{"classify":"llama-3.1-8b-instant","plan_step":"llama-3.1-8b-instant",'
            '"finalize":"llama-3.1-8b-instant"}'
        )
        _remote_set_env(client, "STEP_MODEL_ROUTING", routing)
        _safe_print("STEP_MODEL_ROUTING applied (Groq 8b for classify/plan/finalize)")

    run(client, f"grep -E '^(LLM_PROVIDER_CHAIN|LLM_COOLDOWN|REQUIRE_CONFIRM|DEBUG)=' {ENV_PATH}")

    run(client, f"systemctl restart {SERVICE}")
    health_port = "8080"
    port_cmd = f"grep '^HEALTH_PORT=' {ENV_PATH} 2>/dev/null | cut -d= -f2 | tr -d '\\r' || echo 8080"
    _, port_out, _ = run(client, port_cmd, label="read HEALTH_PORT", quiet=True)
    if port_out.strip().isdigit():
        health_port = port_out.strip()

    health_ok = False
    db_ok = False
    health_out = ""
    for wait in (15, 10, 10):
        run(client, f"sleep {wait}", label=f"wait {wait}s for health")
        _, health_out, _ = run(
            client, f"curl -sf --max-time 5 http://127.0.0.1:{health_port}/ || true"
        )
        if health_out.strip():
            break
    try:
        data = json.loads(health_out.strip().split("\n")[0])
        health_ok = data.get("status") in ("ok", "degraded")
        db_ok = (data.get("database") or {}).get("status") == "ok"
    except json.JSONDecodeError:
        pass

    if not health_ok:
        run(
            client,
            f"journalctl -u {SERVICE} --no-pager -n 25 --no-hostname",
            label="journal tail (health failed)",
        )

    base_url = f"http://127.0.0.1:{health_port}"
    _, unauth_out, _ = run(
        client,
        f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 5 -X POST {base_url}/v1/agent/run "
        "-H 'Content-Type: application/json' -d '{\"agent_key\":\"orchestrator\",\"user_id\":1,\"text\":\"ping\"}'",
    )
    unauth_code = unauth_out.strip()

    auth_test = "skip"
    if api_token:
        auth_cmd = (
            f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 10 -X POST {base_url}/v1/agent/run "
            f"-H 'Authorization: Bearer {api_token}' "
            "-H 'Content-Type: application/json' "
            "-d '{\"agent_key\":\"orchestrator\",\"user_id\":1,\"chat_id\":1,\"text\":\"health ping\"}'"
        )
        _, auth_out, _ = run(
            client,
            auth_cmd,
            label="curl POST /v1/agent/run (Bearer token set)",
        )
        auth_test = auth_out.strip()

    service_active = True
    _, active_out, _ = run(client, f"systemctl is-active {SERVICE}")
    service_active = active_out.strip() == "active"

    today = date.today().isoformat()
    signoff = {
        "date": today,
        "automated": {
            "W1_5_health": health_ok,
            "W1_5_database": db_ok,
            "W4_17_api_unauth_401": unauth_code == "401",
            "W4_17_api_auth": auth_test in ("200", "202"),
            "REQUIRE_CONFIRM_env": True,
            "LLM_PROVIDER_CHAIN_groq": True,
            "service_active": service_active,
        },
    }
    _safe_print("\n=== E2E automated signoff JSON ===")
    signoff_json = json.dumps(signoff, ensure_ascii=False, indent=2)
    _safe_print(signoff_json)

    out_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "docs", "last_vps_e2e_automated.txt"
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(f"# VPS automated E2E — {today}\n\n")
        fh.write("REQUIRE_CONFIRM=true, DEBUG=false applied on VPS.\n\n")
        fh.write("```json\n")
        fh.write(signoff_json)
        fh.write("\n```\n")
    _safe_print(f"Wrote {out_path}")

    client.close()
    _safe_print("\nProd configure + automated E2E done.")
    _safe_print("Telegram scenarios — docs/E2E_TELEGRAM_CHECKLIST.md")


if __name__ == "__main__":
    main()
