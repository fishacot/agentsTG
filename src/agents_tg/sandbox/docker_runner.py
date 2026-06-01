"""Docker sandbox runner — Python code execution without network."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SEC = 30


async def run_code(
    code: str,
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    language: str = "python",
) -> dict[str, str]:
    """Execute Python code in isolated subprocess (no network)."""
    if language != "python":
        return {"ok": "false", "error": f"unsupported language: {language}"}

    code = (code or "").strip()
    if not code:
        return {"ok": "false", "error": "empty code"}

    blocked = ("import os", "import subprocess", "open(", "__import__", "eval(", "exec(")
    low = code.lower()
    for b in blocked:
        if b.lower() in low:
            return {"ok": "false", "error": f"blocked construct: {b}"}

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        script_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "python",
            script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_sec
            )
        except asyncio.TimeoutError:
            proc.kill()
            return {"ok": "false", "error": f"timeout after {timeout_sec}s"}

        out = stdout.decode("utf-8", errors="replace")[:4000]
        err = stderr.decode("utf-8", errors="replace")[:1000]
        ok = proc.returncode == 0
        return {
            "ok": str(ok).lower(),
            "stdout": out,
            "stderr": err,
            "exit_code": str(proc.returncode or 0),
        }
    except FileNotFoundError:
        return {"ok": "false", "error": "python interpreter not found"}
    except Exception as exc:
        return {"ok": "false", "error": str(exc)}
    finally:
        try:
            Path(script_path).unlink(missing_ok=True)
        except Exception:
            pass


run_python_code = run_code
