#!/usr/bin/env python3
"""Cursor hook: quick ruff check after Python file edits (src/ or tests/)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    path_str = (
        payload.get("file_path")
        or payload.get("path")
        or payload.get("editedFile")
        or ""
    )
    if not path_str:
        return 0

    path = Path(path_str.replace("\\", "/"))
    if path.suffix != ".py":
        return 0
    parts = path.parts
    if "src" not in parts and "tests" not in parts:
        return 0

    root = Path.cwd()
    target = path if path.is_file() else root / path
    if not target.is_file():
        return 0

    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", str(target)],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0

    if result.returncode == 0:
        return 0

    msg = (result.stdout or result.stderr or "").strip()[:800]
    print(json.dumps({"additional_context": f"Ruff после правки {path}:\n{msg}"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
