"""Git synchronization utility for Obsidian vault."""

import logging
import subprocess
from pathlib import Path

from src.agents_tg.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GitSync:
    """Utility to sync a directory with a Git repository."""

    def __init__(self, path: str, remote_url: str = "") -> None:
        self.path = Path(path)
        self.remote_url = remote_url

        if not self.path.exists():
            self.path.mkdir(parents=True)

        if not (self.path / ".git").exists():
            self._run_git("init")
            if self.remote_url:
                self._run_git(f"remote add origin {self.remote_url}")

    def _run_git(self, command: str) -> str:
        """Run a git command in the vault directory."""
        try:
            cmd = f"git {command}"
            result = subprocess.run(
                cmd,
                cwd=self.path,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.cmd} - {e.stderr}")
            return f"Error: {e.stderr}"

    def pull(self) -> str:
        """Pull changes from remote."""
        if not self.remote_url:
            return "No remote URL configured."
        return self._run_git("pull origin main")

    def sync(self, message: str = "Sync by AI Assistant") -> str:
        """Add, commit and push changes."""
        self._run_git("add .")

        # Check if there are changes to commit
        status = self._run_git("status --porcelain")
        if not status:
            return "No changes to sync."

        self._run_git(f'commit -m "{message}"')

        if self.remote_url:
            return self._run_git("push origin main")
        return "Changes committed locally."


# Singleton instance for Obsidian
obsidian_sync = GitSync(settings.OBSIDIAN_VAULT_PATH, settings.GIT_REMOTE_URL)
