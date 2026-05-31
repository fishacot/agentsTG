"""Deploy agentsTG to FirstByte VPS via git pull + systemd restart.

Requires env VPS_SSH_PASSWORD (never commit passwords).
"""
from __future__ import annotations

import os
import sys

import paramiko

HOST = "91.186.221.32"
USER = "root"
REPO = "/opt/agentsTG"
SERVICE = "agents-tg"
BRANCH = "master"


def _safe_print(text: str) -> None:
    """Print without UnicodeEncodeError on Windows cp1251 consoles."""
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        sys.stdout.write(text + "\n")
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode(enc, errors="replace"))
    sys.stdout.flush()


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    _safe_print(f"\n=== {cmd} ===")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        _safe_print(out.rstrip())
    if err.strip():
        _safe_print("STDERR: " + err.rstrip())
    return code, out, err


def main() -> None:
    password = os.environ.get("VPS_SSH_PASSWORD", "")
    if not password:
        print("Set VPS_SSH_PASSWORD", file=sys.stderr)
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=password, timeout=20)

    alembic_cmd = (
        f"cd {REPO} && "
        "if [ -f .env ] && grep -q '^DATABASE_URL=.*@' .env; then "
        "sudo -u botsuser bash -lc 'cd /opt/agentsTG && "
        "source .venv/bin/activate 2>/dev/null || true; "
        "poetry run alembic upgrade head 2>&1 || python -m alembic upgrade head 2>&1'; "
        "else echo 'SKIP alembic: DATABASE_URL not configured'; fi"
    )

    steps = [
        f"cd {REPO} && git fetch origin {BRANCH}",
        f"cd {REPO} && git reset --hard origin/{BRANCH}",
        f"cd {REPO} && git log -1 --oneline",
        f"cd {REPO} && test -f workspace/HEARTBEAT.default.md && echo HEARTBEAT.default.md OK || echo HEARTBEAT.default.md MISSING",
        alembic_cmd,
        f"cd {REPO} && sudo -u botsuser bash -lc 'poetry install --no-interaction --no-ansi 2>&1 | tail -5' || true",
        f"systemctl restart {SERVICE}",
        "sleep 8",
        f"systemctl is-active {SERVICE}",
        "curl -sf http://127.0.0.1:8080/ || curl -s http://127.0.0.1:8080/ || true",
        f"journalctl -u {SERVICE} --no-pager -n 12 --no-hostname",
    ]
    for cmd in steps:
        code, _, _ = run(client, cmd)
        if code != 0 and "poetry install" not in cmd and "alembic" not in cmd:
            _safe_print(f"Deploy step failed (exit {code}): {cmd}")
            client.close()
            sys.exit(code)

    client.close()
    _safe_print("\nDeploy complete.")


if __name__ == "__main__":
    main()
