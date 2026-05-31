"""Configure Neon DATABASE_URL on VPS and run alembic + restart.

Requires env (never commit):
  VPS_SSH_PASSWORD — root SSH password for 91.186.221.32
  NEON_DATABASE_URL — postgresql://... or postgresql+asyncpg://...@....neon.tech/...?sslmode=require

Optional: DATABASE_URL if it already points at neon.tech
"""
from __future__ import annotations

import os
import re
import sys

import paramiko

from vps_deploy import HOST, POETRY, REPO, SERVICE, USER, _safe_print, run

MASK = re.compile(r"://([^:@/]+):([^@/]+)@")


def _mask(s: str) -> str:
    return MASK.sub(r"://\1:***@", s)


def _neon_url() -> str:
    url = os.environ.get("NEON_DATABASE_URL", "").strip()
    if not url:
        url = os.environ.get("DATABASE_URL", "").strip()
    if not url or "neon.tech" not in url:
        print("Set NEON_DATABASE_URL (neon.tech connection string)", file=sys.stderr)
        sys.exit(1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


def _patch_env(client: paramiko.SSHClient, updates: dict[str, str]) -> None:
    """Update .env via SFTP (safe for special chars in URLs)."""
    path = f"{REPO}/.env"
    sftp = client.open_sftp()
    try:
        with sftp.open(path, "r") as remote:
            lines = remote.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        lines = []
    sftp.close()

    out_lines: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if not line.strip() or line.strip().startswith("#"):
            out_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            out_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out_lines.append(line)
    for key, val in updates.items():
        if key not in seen:
            out_lines.append(f"{key}={val}")
        _safe_print(f"Set {key}={_mask(val)}")

    sftp = client.open_sftp()
    with sftp.open(path, "w") as remote:
        remote.write(("\n".join(out_lines) + "\n").encode("utf-8"))
    sftp.close()


def main() -> None:
    password = os.environ.get("VPS_SSH_PASSWORD", "")
    if not password:
        print("Set VPS_SSH_PASSWORD", file=sys.stderr)
        sys.exit(1)

    db_url = _neon_url()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=password, timeout=20)

    _patch_env(
        client,
        {"DATABASE_URL": db_url, "APP_TIMEZONE": "Europe/Moscow"},
    )

    steps = [
        (
            f"cd {REPO} && sudo -u botsuser bash -lc 'cd {REPO} && "
            f"PYTHONPATH={REPO} {POETRY} run alembic upgrade head 2>&1'"
        ),
        (
            f"cd {REPO} && sudo -u botsuser bash -lc "
            f"'cd {REPO} && {POETRY} install --no-interaction --no-ansi 2>&1 | tail -8'"
        ),
        f"systemctl restart {SERVICE}",
        "sleep 8",
        f"systemctl is-active {SERVICE}",
        (
            f"journalctl -u {SERVICE} --no-pager -n 25 --no-hostname | "
            "grep -E 'Database connected|without persistence|ConnectionRefused' || true"
        ),
        (
            f"cd {REPO} && sudo -u botsuser bash -lc 'cd {REPO} && "
            f"PYTHONPATH={REPO} python3 scripts/agent_status.py 2>&1 | head -20'"
        ),
    ]
    for cmd in steps:
        code, _, _ = run(client, cmd)
        if code != 0 and "alembic" not in cmd and "poetry install" not in cmd:
            client.close()
            sys.exit(code)

    client.close()
    _safe_print("\nNeon configure complete.")


if __name__ == "__main__":
    main()
