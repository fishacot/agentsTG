#!/usr/bin/env python3
"""Cursor hook: remind agent to run verify + update implementation-notes on stop."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _git_diff_names() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode != 0:
            out = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        return [ln.strip() for ln in (out.stdout or "").splitlines() if ln.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def main() -> int:
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass

    changed = _git_diff_names()
    py_changed = [p for p in changed if p.startswith("src/") or p.startswith("tests/")]
    if not py_changed:
        return 0

    context = (
        "Перед завершением сессии (если менялся src/ или tests/):\n"
        "1. `python -m pytest tests/ -v --tb=short` (см. docs/PROJECT_VERIFICATION.md)\n"
        "2. Обновить docs/implementation-notes.md\n"
        f"Изменённые файлы: {', '.join(py_changed[:8])}"
    )
    print(json.dumps({"followup_message": context}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
