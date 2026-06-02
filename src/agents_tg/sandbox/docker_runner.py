"""Sandbox runner — subprocess (default) or optional Docker isolation."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

from src.agents_tg.config.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SEC = 30

_BLOCKED = (
    "import os",
    "import subprocess",
    "open(",
    "__import__",
    "eval(",
    "exec(",
)


def _validate_code(code: str) -> dict[str, str] | None:
    code = (code or "").strip()
    if not code:
        return {"ok": "false", "error": "empty code"}
    low = code.lower()
    for b in _BLOCKED:
        if b.lower() in low:
            return {"ok": "false", "error": f"blocked construct: {b}"}
    return None


async def _run_subprocess(script_path: str, *, timeout_sec: int) -> dict[str, str]:
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
        "sandbox": "subprocess",
    }


async def _run_docker(
    code: str, *, timeout_sec: int, image: str
) -> dict[str, str]:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        script_path = f.name

    host_dir = str(Path(script_path).parent)
    script_name = Path(script_path).name
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-v",
        f"{host_dir}:/work:ro",
        "-w",
        "/work",
        image,
        "python",
        script_name,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_sec + 5
            )
        except asyncio.TimeoutError:
            proc.kill()
            return {"ok": "false", "error": f"docker timeout after {timeout_sec}s"}
        out = stdout.decode("utf-8", errors="replace")[:4000]
        err = stderr.decode("utf-8", errors="replace")[:1000]
        ok = proc.returncode == 0
        return {
            "ok": str(ok).lower(),
            "stdout": out,
            "stderr": err,
            "exit_code": str(proc.returncode or 0),
            "sandbox": "docker",
        }
    except FileNotFoundError:
        logger.warning("docker not found, falling back to subprocess")
        return await _run_subprocess(script_path, timeout_sec=timeout_sec)
    except Exception as exc:
        return {"ok": "false", "error": str(exc), "sandbox": "docker"}
    finally:
        try:
            Path(script_path).unlink(missing_ok=True)
        except Exception:
            pass


async def run_code(
    code: str,
    *,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    language: str = "python",
) -> dict[str, str]:
    """Execute Python in subprocess or Docker (SANDBOX_MODE)."""
    if language != "python":
        return {"ok": "false", "error": f"unsupported language: {language}"}

    err = _validate_code(code)
    if err:
        return err

    settings = get_settings()
    mode = (settings.SANDBOX_MODE or "subprocess").strip().lower()
    body = code.strip()

    if mode == "docker":
        return await _run_docker(
            body,
            timeout_sec=timeout_sec,
            image=settings.SANDBOX_DOCKER_IMAGE,
        )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(body)
        script_path = f.name

    try:
        return await _run_subprocess(script_path, timeout_sec=timeout_sec)
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
