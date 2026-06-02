"""Sandbox subprocess mode."""

import pytest

from src.agents_tg.sandbox.docker_runner import run_code


@pytest.mark.asyncio
async def test_run_code_subprocess_print():
    out = await run_code("print(2+2)", timeout_sec=10)
    assert out["ok"] == "true"
    assert "4" in out.get("stdout", "")
