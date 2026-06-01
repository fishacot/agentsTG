"""Lightweight HTTP health + gateway endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_server_task: asyncio.Task | None = None
_db_engine: Any = None


def set_db_engine(engine: Any) -> None:
    global _db_engine
    _db_engine = engine


async def _ping_database() -> dict[str, Any]:
    if _db_engine is None:
        return {"status": "unavailable", "reason": "no engine configured"}
    try:
        from sqlalchemy import text

        async with _db_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        logger.debug("Database ping failed: %s", exc)
        return {"status": "error", "reason": str(exc)[:120]}


async def _pg_status() -> dict[str, Any]:
    """Public helper for /status command."""
    db = await _ping_database()
    return {"connected": db.get("status") == "ok", **db}


async def _build_health_body() -> bytes:
    db = await _ping_database()
    payload = {
        "status": "ok" if db.get("status") == "ok" else "degraded",
        "service": "agents-tg",
        "database": db,
    }
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode()


def _parse_request(raw: bytes) -> tuple[str, str, dict[str, Any]]:
    """Parse HTTP request line, path, and JSON body."""
    try:
        header_end = raw.index(b"\r\n\r\n")
        headers = raw[:header_end].decode("utf-8", errors="replace")
        body_raw = raw[header_end + 4 :]
    except ValueError:
        return "GET", "/", {}

    lines = headers.split("\r\n")
    parts = lines[0].split(" ") if lines else ["GET", "/", "HTTP/1.1"]
    method = parts[0].upper() if parts else "GET"
    path = parts[1].split("?")[0] if len(parts) > 1 else "/"

    body: dict[str, Any] = {}
    if body_raw.strip():
        try:
            parsed = json.loads(body_raw.decode("utf-8"))
            body = parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            body = {}
    return method, path, body


async def _handle_agent_run(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    from src.agents_tg.gateway.envelope import OpenClawEnvelope
    from src.agents_tg.gateway.router import gateway_router

    agent_key = str(body.get("agent_key", "personal_assistant"))
    user_id = int(body.get("user_id", 0))
    chat_id = int(body.get("chat_id", user_id))
    text = str(body.get("text", ""))
    message_id = int(body.get("message_id", 0))

    envelope = OpenClawEnvelope(
        chat_id=chat_id,
        user_id=user_id,
        text=text,
        message_id=message_id or 1,
        agent_key=agent_key,
    )
    result = await gateway_router.dispatch(envelope, trigger="http")
    return 200, {
        "session_id": result.session_id,
        "job_id": result.job_id,
        "duplicate": result.duplicate,
    }


async def _handle_a2a_callback(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    from src.agents_tg.gateway.router import gateway_router

    payload = await gateway_router.handle_a2a_callback(body)
    code = 200 if payload.get("ok") else 400
    return code, payload


async def _handle_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        raw = await reader.readuntil(b"\r\n\r\n")
        content_length = 0
        for line in raw.decode("utf-8", errors="replace").split("\r\n"):
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())
        body_bytes = b""
        if content_length > 0:
            body_bytes = await reader.readexactly(content_length)
        method, path, body = _parse_request(raw + body_bytes)

        status_code = 200
        if method == "GET" and path in ("/", "/health", "/healthz"):
            response_body = await _build_health_body()
        elif method == "POST" and path == "/v1/agent/run":
            status_code, data = await _handle_agent_run(body)
            response_body = (json.dumps(data, ensure_ascii=False) + "\n").encode()
        elif method == "POST" and path == "/v1/webhook/a2a/callback":
            status_code, data = await _handle_a2a_callback(body)
            response_body = (json.dumps(data, ensure_ascii=False) + "\n").encode()
        else:
            status_code = 404
            response_body = b'{"error":"not found"}\n'

        reason = "OK" if status_code == 200 else "Not Found" if status_code == 404 else "Bad Request"
        response = (
            f"HTTP/1.1 {status_code} {reason}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(response_body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode() + response_body
        writer.write(response)
        await writer.drain()
    except Exception as exc:
        logger.debug("HTTP request error: %s", exc)
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

    server = await asyncio.start_server(_handle_request, host, port)

    async def _serve() -> None:
        async with server:
            await server.serve_forever()

    _server_task = asyncio.create_task(_serve())
    logger.info("Health/gateway server listening on %s:%s", host, port)


async def stop_health_server() -> None:
    global _server_task
    if _server_task:
        _server_task.cancel()
        try:
            await _server_task
        except asyncio.CancelledError:
            pass
        _server_task = None
