"""Lightweight HTTP health endpoint."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_server_task: asyncio.Task | None = None


async def _handle_health(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        await reader.readuntil(b"\r\n\r\n")
        body = b'{"status":"ok","service":"agents-tg"}\n'
        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + body
        )
        writer.write(response)
        await writer.drain()
    except Exception as exc:
        logger.debug("Health request error: %s", exc)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def start_health_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    global _server_task
    if _server_task and not _server_task.done():
        return

    server = await asyncio.start_server(_handle_health, host, port)

    async def _serve() -> None:
        async with server:
            await server.serve_forever()

    _server_task = asyncio.create_task(_serve())
    logger.info("Health server listening on %s:%s", host, port)


async def stop_health_server() -> None:
    global _server_task
    if _server_task:
        _server_task.cancel()
        try:
            await _server_task
        except asyncio.CancelledError:
            pass
        _server_task = None
