"""Fetch recent agents-tg logs (incident debug)."""
from __future__ import annotations

import os
import sys

import paramiko

HOST = "91.186.221.32"
OUT = "docs/last_incident_elza.txt"


def main() -> None:
    password = os.environ.get("VPS_SSH_PASSWORD", "")
    if not password:
        sys.exit("Set VPS_SSH_PASSWORD")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username="root", password=password, timeout=25)
    cmds = [
        "systemctl is-active agents-tg",
        "journalctl -u agents-tg --no-pager -n 150 --no-hostname",
        "grep REQUIRE_CONFIRM /opt/agentsTG/.env || true",
        "curl -s http://127.0.0.1:8080/",
    ]
    parts: list[str] = []
    for cmd in cmds:
        _, o, e = c.exec_command(cmd, timeout=90)
        parts.append(
            f"=== {cmd} ===\n"
            + o.read().decode("utf-8", errors="replace")
            + e.read().decode("utf-8", errors="replace")
        )
    c.close()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(OUT)


if __name__ == "__main__":
    main()
