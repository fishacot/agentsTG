#!/usr/bin/env python3
"""Cursor hook: warn before destructive shell commands."""
from __future__ import annotations

import json
import re
import sys

BLOCK_PATTERNS = [
    r"git\s+push\s+.*--force",
    r"git\s+reset\s+--hard",
    r"rm\s+-rf",
    r"Remove-Item\s+.*-Recurse",
    r"del\s+/s",
    r"format\s+[a-z]:",
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print('{"permission": "allow"}')
        return 0

    command = payload.get("command") or ""
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, command, re.I):
            print(
                json.dumps(
                    {
                        "permission": "ask",
                        "user_message": f"Опасная команда: {command[:120]}",
                        "agent_message": "Hook запросил подтверждение destructive-команды.",
                    },
                    ensure_ascii=False,
                )
            )
            return 0

    print('{"permission": "allow"}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
