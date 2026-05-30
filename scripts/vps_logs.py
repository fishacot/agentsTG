"""Fetch agents-tg logs from VPS (one-off debug)."""
import os
import sys

import paramiko

HOST = "91.186.221.32"
USER = "root"
PASSWORD = os.environ.get("VPS_SSH_PASSWORD", "")


def main() -> None:
    if not PASSWORD:
        print("Set VPS_SSH_PASSWORD", file=sys.stderr)
        sys.exit(1)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=PASSWORD, timeout=20)
    cmds = [
        "systemctl is-active agents-tg",
        "journalctl -u agents-tg --no-pager -n 200",
        "grep -E 'personal_assistant|ERROR|Exception|Traceback|429|NO_REPLY|debounce|duplicate' /var/log/syslog 2>/dev/null | tail -50 || true",
    ]
    out_path = os.path.join(os.path.dirname(__file__), "..", "vps_logs_out.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for cmd in cmds:
            f.write(f"\n=== {cmd} ===\n\n")
            _, o, e = c.exec_command(cmd, timeout=90)
            out = o.read().decode("utf-8", errors="replace")
            err = e.read().decode("utf-8", errors="replace")
            f.write(out)
            if err.strip():
                f.write("STDERR: " + err)
    print(f"Wrote {out_path}")
    c.close()


if __name__ == "__main__":
    main()
