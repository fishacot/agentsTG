"""Create Neon EU project (or reuse existing) and print connection string.

Requires env NEON_API_KEY (Neon Console → Account → API keys). Never commit the key.

Usage:
  $env:NEON_API_KEY = '...'
  python scripts/neon_provision.py
  # then copy output to NEON_DATABASE_URL for vps_configure_neon.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API_BASE = "https://console.neon.tech/api/v2"
PROJECT_NAME = "agentsTG"
REGION_ID = "aws-eu-central-1"


def _request(method: str, path: str, body: dict | None = None) -> dict:
    key = os.environ.get("NEON_API_KEY", "").strip()
    if not key:
        print("Set NEON_API_KEY (Neon Console → Account → API keys)", file=sys.stderr)
        sys.exit(1)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"Neon API {e.code}: {err[:500]}", file=sys.stderr)
        sys.exit(1)


def _connection_uri(project_id: str) -> str:
    q = "database_name=neondb&role_name=neondb_owner&pooled=false"
    data = _request("GET", f"/projects/{project_id}/connection_uri?{q}")
    uri = data.get("uri") or data.get("connection_uri") or ""
    if not uri:
        print(f"No URI in response: {list(data.keys())}", file=sys.stderr)
        sys.exit(1)
    return uri


def main() -> None:
    listed = _request("GET", "/projects")
    projects = listed.get("projects") or []
    project_id = ""
    for p in projects:
        if p.get("name") == PROJECT_NAME:
            project_id = p.get("id", "")
            print(f"Found existing project {PROJECT_NAME} id={project_id}")
            break

    if not project_id:
        created = _request(
            "POST",
            "/projects",
            {"project": {"name": PROJECT_NAME, "region_id": REGION_ID}},
        )
        proj = created.get("project") or created
        project_id = proj.get("id", "")
        if not project_id:
            print("Create project response missing id", file=sys.stderr)
            sys.exit(1)
        print(f"Created project {PROJECT_NAME} id={project_id} region={REGION_ID}")

    uri = _connection_uri(project_id)
    if "neon.tech" not in uri:
        print("Unexpected URI host", file=sys.stderr)
        sys.exit(1)
    # Mask password in stdout hint only
    safe = uri
    if "@" in uri and "://" in uri:
        pre, rest = uri.split("://", 1)
        if "@" in rest:
            userpart, hostpart = rest.rsplit("@", 1)
            if ":" in userpart:
                user = userpart.split(":", 1)[0]
                safe = f"{pre}://{user}:***@{hostpart}"
    print(f"\nConnection string (set NEON_DATABASE_URL, do not commit):\n{uri}")
    print(f"\nMasked: {safe}")
    print("\nNext:")
    print("  $env:NEON_DATABASE_URL = '<uri above>'")
    print("  $env:VPS_SSH_PASSWORD = '...'")
    print("  python scripts/vps_configure_neon.py")


if __name__ == "__main__":
    main()
