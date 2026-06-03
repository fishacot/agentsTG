"""GitHub REST integration (read issues)."""

from __future__ import annotations

from typing import Any

import httpx

from src.agents_tg.config.settings import get_settings
from src.agents_tg.services.integrations.base import IntegrationError, audit_integration


async def list_github_issues(
    *,
    user_id: str,
    repo: str,
    state: str = "open",
    limit: int = 10,
) -> dict[str, Any]:
    settings = get_settings()
    token = getattr(settings, "GITHUB_TOKEN", None) or ""
    if not token.strip():
        return {
            "ok": False,
            "error": "GITHUB_TOKEN not configured",
            "hint": "Добавьте GITHUB_TOKEN в .env (read:issues).",
        }

    repo = repo.strip().replace("https://github.com/", "").strip("/")
    if "/" not in repo:
        raise IntegrationError("repo must be owner/name")

    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    params = {"state": state, "per_page": min(limit, 30)}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers, params=params)
        if resp.status_code >= 400:
            raise IntegrationError(f"github {resp.status_code}: {resp.text[:200]}")
        raw = resp.json()
        issues = []
        for item in raw if isinstance(raw, list) else []:
            if item.get("pull_request") is not None:
                continue
            href = str(item.get("html_url") or "")
            if "/pull/" in href:
                continue
            issues.append(
                {
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "url": item.get("html_url"),
                    "state": item.get("state"),
                }
            )
        audit_integration(
            "github",
            user_id=user_id,
            detail=f"listed {len(issues)} issues from {repo}",
        )
        return {"ok": True, "repo": repo, "issues": issues[:limit]}
    except IntegrationError:
        raise
    except Exception as exc:
        raise IntegrationError(str(exc)) from exc
