"""Shared limits for Telegram API connections (Windows-friendly)."""

import asyncio

# Limit parallel connections to api.telegram.org — prevents WinError 121 on Windows
TELEGRAM_CONNECT_SEMAPHORE = asyncio.Semaphore(2)
