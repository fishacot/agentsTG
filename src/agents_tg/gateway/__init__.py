"""L2 Gateway layer — envelope routing, sessions, jobs, hooks."""

from src.agents_tg.gateway.envelope import MediaItem, OpenClawEnvelope
from src.agents_tg.gateway.job_store import job_store
from src.agents_tg.gateway.router import GatewayRouter, gateway_router
from src.agents_tg.gateway.session import session_manager


def register_default_hooks() -> None:
    """Ensure default security hooks are loaded."""
    import src.agents_tg.gateway.hooks  # noqa: F401


def set_engine(engine) -> None:
    job_store.set_engine(engine)


__all__ = [
    "GatewayRouter",
    "MediaItem",
    "OpenClawEnvelope",
    "gateway_router",
    "job_store",
    "register_default_hooks",
    "session_manager",
    "set_engine",
]
