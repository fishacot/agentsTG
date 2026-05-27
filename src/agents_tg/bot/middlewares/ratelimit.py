"""Rate limiting middleware for Telegram bot.

Prevents flood by limiting requests per user per time window.
"""

import logging
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """Simple in-memory rate limiting middleware.

    Limits: 3 messages per 60 seconds per user.
    """

    def __init__(self, limit: int = 3, window: int = 60) -> None:
        """Initialize rate limiter.

        Args:
            limit: Max requests per window per user
            window: Time window in seconds
        """
        super().__init__()
        self.limit = limit
        self.window = window
        self._user_requests: dict[int, list[float]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Check rate limit before processing message."""
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if user_id is None:
            return await handler(event, data)

        now = time.time()
        user_times = self._user_requests.get(user_id, [])

        # Clean old requests outside window
        user_times = [t for t in user_times if now - t < self.window]

        if len(user_times) >= self.limit:
            remaining = self.window - int(now - user_times[0])
            await event.answer(
                f"⏱️ Слишком быстро! Подождите {remaining} сек "
                "перед следующим сообщением."
            )
            logger.warning("Rate limit hit for user %s", user_id)
            return None

        user_times.append(now)
        self._user_requests[user_id] = user_times

        return await handler(event, data)
