"""Health server /v1/models stub."""

import pytest

from src.agents_tg.services import health_server


@pytest.mark.asyncio
async def test_v1_models_route():
    raw = b"GET /v1/models HTTP/1.1\r\nHost: localhost\r\n\r\n"
    method, path, body = health_server._parse_request(raw)
    assert method == "GET"
    assert path == "/v1/models"
    assert body == {}
