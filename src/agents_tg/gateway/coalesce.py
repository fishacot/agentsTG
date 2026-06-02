"""Merge consecutive short outbound blocks within an idle window (OpenClaw idleMs)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BlockCoalescer:
    """Buffer outbound text blocks; merge short bursts before commit."""

    idle_ms: int
    short_limit: int = 256
    separator: str = "\n"
    _pending: str = field(default="", init=False, repr=False)
    _last_ms: int | None = field(default=None, init=False, repr=False)
    _committed: list[str] = field(default_factory=list, init=False, repr=False)

    @property
    def pending(self) -> str:
        """Text not yet committed (for live preview)."""
        return self._pending

    @property
    def preview_text(self) -> str:
        """All text visible during a run (committed + pending)."""
        parts = list(self._committed)
        if self._pending:
            parts.append(self._pending)
        return self.separator.join(parts) if parts else ""

    def push(self, text: str, now_ms: int) -> None:
        cleaned = (text or "").strip()
        if not cleaned:
            return

        if self._pending and self._last_ms is not None:
            delta = now_ms - self._last_ms
            if delta <= self.idle_ms and self._should_merge(self._pending, cleaned):
                self._pending = f"{self._pending}{self.separator}{cleaned}"
                self._last_ms = now_ms
                return
            self._commit_pending()

        self._pending = cleaned
        self._last_ms = now_ms

    def flush(self, now_ms: int | None = None) -> list[str]:
        """Commit pending buffer and return all blocks for delivery."""
        del now_ms  # reserved for future time-based auto-flush
        if self._pending:
            self._commit_pending()
        out = list(self._committed)
        self._committed.clear()
        self._last_ms = None
        return out

    def _should_merge(self, pending: str, new: str) -> bool:
        return len(pending) <= self.short_limit and len(new) <= self.short_limit

    def _commit_pending(self) -> None:
        if self._pending:
            self._committed.append(self._pending)
            self._pending = ""
