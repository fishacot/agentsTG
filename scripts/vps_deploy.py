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


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    print(f"\n=== {cmd} ===")
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print("STDERR:", err.rstrip())
    return code, out, err


def main() -> None:
    password = os.environ.get("VPS_SSH_PASSWORD", "")
    if not password:
        print("Set VPS_SSH_PASSWORD", file=sys.stderr)
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=password, timeout=20)

    steps = [
        f"cd {REPO} && git fetch origin {BRANCH}",
        f"cd {REPO} && git reset --hard origin/{BRANCH}",
        f"cd {REPO} && git log -1 --oneline",
        f"cd {REPO} && poetry install --no-interaction --no-ansi 2>&1 | tail -5",
        f"systemctl restart {SERVICE}",
        "sleep 8",
        f"systemctl is-active {SERVICE}",
        "curl -sf http://127.0.0.1:8080/ || curl -s http://127.0.0.1:8080/ || true",
        f"journalctl -u {SERVICE} --no-pager -n 8 --no-hostname",
    ]
    for cmd in steps:
        code, _, _ = run(client, cmd)
        if code != 0 and "poetry install" not in cmd:
            print(f"Deploy step failed (exit {code}): {cmd}", file=sys.stderr)
            client.close()
            sys.exit(code)

    client.close()
    print("\nDeploy complete.")


if __name__ == "__main__":
    main()
