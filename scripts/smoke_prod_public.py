"""Public prod smoke (no SSH): health + API 401. Writes docs/last_vps_public_smoke.txt."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

HOST = os.environ.get("VPS_HEALTH_HOST", "91.186.221.32")
PORT = os.environ.get("HEALTH_PORT", "8080")
BASE = f"http://{HOST}:{PORT}"


def _get(path: str) -> tuple[int, str]:
    req = urllib.request.Request(f"{BASE}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def _post_agent_run() -> int:
    data = json.dumps(
        {"agent_key": "orchestrator", "user_id": 1, "text": "ping"}
    ).encode()
    req = urllib.request.Request(
        f"{BASE}/v1/agent/run",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main() -> None:
    health_code, health_body = _get("/")
    health_ok = False
    db_ok = False
    try:
        payload = json.loads(health_body.strip())
        health_ok = payload.get("status") in ("ok", "degraded")
        db_ok = (payload.get("database") or {}).get("status") == "ok"
    except json.JSONDecodeError:
        pass

    api_unauth = _post_agent_run()
    today = date.today().isoformat()
    report = {
        "date": today,
        "host": HOST,
        "health_http": health_code,
        "health_ok": health_ok,
        "database_ok": db_ok,
        "api_unauth_401": api_unauth == 401,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)

    out = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "docs",
        "last_vps_public_smoke.txt",
    )
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"# Public prod smoke — {today}\n\n```json\n{text}\n```\n")
    print(f"Wrote {out}", file=sys.stderr)

    if not (health_ok and api_unauth == 401):
        sys.exit(1)


if __name__ == "__main__":
    main()
